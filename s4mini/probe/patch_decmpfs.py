import os
p = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/decmpfs.c")
s = open(p).read()
assert "ZlibXattrReg" not in s

code = r'''
#pragma mark --- built-in zlib decompressors (types 3 and 4) ---

/*
 * iOS root filesystems store most binaries HFS-compressed. On real devices the zlib decoders come
 * from the AppleFSCompressionTypeZlib kext; this kernel has no kexts, so provide them here.
 *   type 3: zlib stream (or raw data if the first byte's low nibble is 0xF) right after the
 *           decmpfs header inside the com.apple.decmpfs xattr.
 *   type 4: data in the resource fork: big-endian rsrc header (data offset at byte 0), then at
 *           data offset a BE length word, then little-endian block count and {offset,size} table
 *           (offsets relative to data offset + 4); each block inflates to 64 KiB (raw if it
 *           starts with 0xFF).
 */
#include <libkern/zlib.h>
#include <libkern/OSByteOrder.h>
#include <kern/kalloc.h>

#define DZ_BLOCK 65536U

static void *
dz_alloc(__unused void *opaque, u_int items, u_int size)
{
    size_t n = (size_t)items * size + sizeof(size_t);
    size_t *p = (size_t *)kalloc(n);
    if (p == NULL)
        return NULL;
    p[0] = n;
    return p + 1;
}

static void
dz_free(__unused void *opaque, void *ptr)
{
    size_t *p;
    if (ptr == NULL)
        return;
    p = ((size_t *)ptr) - 1;
    kfree(p, p[0]);
}

static int
dz_inflate(const unsigned char *in, size_t inlen, unsigned char *out, size_t outlen, size_t *produced)
{
    z_stream zs;
    int r;

    *produced = 0;
    if (inlen == 0)
        return 0;
    if ((in[0] & 0x0F) == 0x0F) {
        size_t n = inlen - 1;
        if (n > outlen)
            n = outlen;
        memcpy(out, in + 1, n);
        *produced = n;
        return 0;
    }
    bzero(&zs, sizeof(zs));
    zs.zalloc = dz_alloc;
    zs.zfree = dz_free;
    if (inflateInit(&zs) != Z_OK)
        return EIO;
    zs.next_in = (Bytef *)(uintptr_t)in;
    zs.avail_in = (uInt)inlen;
    zs.next_out = out;
    zs.avail_out = (uInt)outlen;
    r = inflate(&zs, Z_FINISH);
    *produced = outlen - zs.avail_out;
    inflateEnd(&zs);
    if (r == Z_STREAM_END || r == Z_OK || r == Z_BUF_ERROR)
        return 0;
    return EIO;
}

/* copy the part of [src_off, src_off+src_len) that overlaps the request into the vectors */
static void
dz_copy_out(const unsigned char *src, off_t src_off, size_t src_len,
            off_t offset, user_ssize_t size, int nvec, decmpfs_vector *vec)
{
    off_t lo = (offset > src_off) ? offset : src_off;
    off_t hi_req = offset + size, hi_src = src_off + (off_t)src_len;
    off_t hi = (hi_req < hi_src) ? hi_req : hi_src;
    off_t vpos = offset;
    int i;

    if (hi <= lo)
        return;
    for (i = 0; i < nvec; i++) {
        off_t vlo = vpos, vhi = vpos + vec[i].size;
        off_t a = (vlo > lo) ? vlo : lo, b = (vhi < hi) ? vhi : hi;
        if (b > a)
            memcpy((char *)vec[i].buf + (a - vlo), src + (a - src_off), (size_t)(b - a));
        vpos = vhi;
    }
}

static int
decmpfs_validate_compressed_file_Zlib(__unused vnode_t vp, __unused vfs_context_t ctx, __unused decmpfs_header *hdr)
{
    return 0;
}

static int
decmpfs_fetch_uncompressed_data_ZlibXattr(__unused vnode_t vp, __unused vfs_context_t ctx, decmpfs_header *hdr, off_t offset, user_ssize_t size, int nvec, decmpfs_vector *vec, uint64_t *bytes_read)
{
    size_t outlen = (size_t)hdr->uncompressed_size, got = 0;
    size_t inlen;
    unsigned char *out;
    int err;

    if (hdr->attr_size < sizeof(decmpfs_disk_header))
        return EINVAL;
    inlen = hdr->attr_size - sizeof(decmpfs_disk_header);
    if (offset >= (off_t)outlen) {
        if (bytes_read) *bytes_read = 0;
        return 0;
    }
    out = (unsigned char *)kalloc(outlen ? outlen : 1);
    if (out == NULL)
        return ENOMEM;
    err = dz_inflate(hdr->attr_bytes, inlen, out, outlen, &got);
    if (err == 0) {
        if (offset + size > (off_t)got)
            size = (off_t)got > offset ? (user_ssize_t)(got - offset) : 0;
        dz_copy_out(out, 0, got, offset, size, nvec, vec);
        if (bytes_read) *bytes_read = size;
    }
    kfree(out, outlen ? outlen : 1);
    return err;
}

static int
dz_rsrc_read(vnode_t vp, off_t off, void *buf, size_t len)
{
    uio_t uio;
    size_t sz = 0;
    int err;

    uio = uio_create(1, off, UIO_SYSSPACE, UIO_READ);
    if (uio == NULL)
        return ENOMEM;
    uio_addiov(uio, CAST_USER_ADDR_T(buf), len);
    err = vn_getxattr(vp, XATTR_RESOURCEFORK_NAME, uio, &sz, XATTR_NOSECURITY, decmpfs_ctx);
    if (err == 0 && uio_resid(uio) != 0)
        err = EIO;
    uio_free(uio);
    return err;
}

static int
decmpfs_fetch_uncompressed_data_ZlibRsrc(vnode_t vp, __unused vfs_context_t ctx, decmpfs_header *hdr, off_t offset, user_ssize_t size, int nvec, decmpfs_vector *vec, uint64_t *bytes_read)
{
    uint32_t hdr4[4], nblocks, first, last, b;
    uint32_t data_off;
    uint32_t *table = NULL;
    unsigned char *cbuf = NULL, *ubuf = NULL;
    size_t cbuf_len = 0, table_len = 0;
    off_t total = (off_t)hdr->uncompressed_size;
    int err;

    if (offset >= total) {
        if (bytes_read) *bytes_read = 0;
        return 0;
    }
    if (offset + size > total)
        size = (user_ssize_t)(total - offset);

    err = dz_rsrc_read(vp, 0, hdr4, sizeof(hdr4));
    if (err) return err;
    data_off = OSSwapBigToHostInt32(hdr4[0]);
    err = dz_rsrc_read(vp, (off_t)data_off + 4, &nblocks, 4);
    if (err) return err;
    nblocks = OSSwapLittleToHostInt32(nblocks);
    if (nblocks == 0 || nblocks > 0x100000U)
        return EINVAL;
    table_len = (size_t)nblocks * 8U;
    table = (uint32_t *)kalloc(table_len);
    ubuf = (unsigned char *)kalloc(DZ_BLOCK);
    if (table == NULL || ubuf == NULL) { err = ENOMEM; goto out; }
    err = dz_rsrc_read(vp, (off_t)data_off + 8, table, table_len);
    if (err) goto out;

    first = (uint32_t)(offset / DZ_BLOCK);
    last = (uint32_t)((offset + size - 1) / DZ_BLOCK);
    if (last >= nblocks) last = nblocks - 1;
    for (b = first; b <= last; b++) {
        uint32_t boff = OSSwapLittleToHostInt32(table[b * 2]);
        uint32_t blen = OSSwapLittleToHostInt32(table[b * 2 + 1]);
        size_t got = 0;
        if (blen > cbuf_len) {
            if (cbuf) kfree(cbuf, cbuf_len);
            cbuf_len = blen;
            cbuf = (unsigned char *)kalloc(cbuf_len);
            if (cbuf == NULL) { cbuf_len = 0; err = ENOMEM; goto out; }
        }
        err = dz_rsrc_read(vp, (off_t)data_off + 4 + boff, cbuf, blen);
        if (err) goto out;
        if (blen && cbuf[0] == 0xFF) {
            got = blen - 1 > DZ_BLOCK ? DZ_BLOCK : blen - 1;
            memcpy(ubuf, cbuf + 1, got);
        } else {
            err = dz_inflate(cbuf, blen, ubuf, DZ_BLOCK, &got);
            if (err) goto out;
        }
        dz_copy_out(ubuf, (off_t)b * DZ_BLOCK, got, offset, size, nvec, vec);
    }
    if (bytes_read) *bytes_read = size;
out:
    if (cbuf) kfree(cbuf, cbuf_len);
    if (ubuf) kfree(ubuf, DZ_BLOCK);
    if (table) kfree(table, table_len);
    return err;
}

static decmpfs_registration ZlibXattrReg =
{
    .decmpfs_registration = DECMPFS_REGISTRATION_VERSION,
    .validate          = decmpfs_validate_compressed_file_Zlib,
    .adjust_fetch      = NULL,
    .fetch             = decmpfs_fetch_uncompressed_data_ZlibXattr,
    .free_data         = NULL,
    .get_flags         = NULL
};

static decmpfs_registration ZlibRsrcReg =
{
    .decmpfs_registration = DECMPFS_REGISTRATION_VERSION,
    .validate          = decmpfs_validate_compressed_file_Zlib,
    .adjust_fetch      = NULL,
    .fetch             = decmpfs_fetch_uncompressed_data_ZlibRsrc,
    .free_data         = NULL,
    .get_flags         = NULL
};

'''

a = "#pragma mark --- decmpfs initialization ---\n"
assert a in s
s = s.replace(a, code + a, 1)
a = "    register_decmpfs_decompressor(CMP_Type1, &Type1Reg);\n"
assert a in s
s = s.replace(a, a + "    register_decmpfs_decompressor(3, &ZlibXattrReg);\n    register_decmpfs_decompressor(4, &ZlibRsrcReg);\n", 1)
open(p, "w").write(s)
print("ok")
