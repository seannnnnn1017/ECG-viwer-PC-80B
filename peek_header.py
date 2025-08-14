# peek_header.py
import sys, os, binascii

def sniff(fp):
    with open(fp, 'rb') as f:
        head = f.read(64)
    print("File:", fp)
    print("Size:", os.path.getsize(fp), "bytes")
    print("Head (ASCII best-effort):", ''.join(chr(b) if 32<=b<=126 else '.' for b in head))
    print("Head (HEX):", binascii.hexlify(head).decode())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python peek_header.py file.SCP")
        sys.exit(1)
    sniff(sys.argv[1])
