; Checked selection of FW2A kernel for the released DOS loader.
; 8086 / DOS 2+, GPL-2.0-or-later. Exit 0 only after full readback comparison.
bits 16
cpu 8086
org 100h
start:
    push cs
    pop ds
    push cs
    pop es
    cld
    mov ax, 3d00h
    mov dx, source
    int 21h
    jc fail
    mov [src], ax
    mov bx, ax
    mov ax, 4202h
    xor cx, cx
    xor dx, dx
    int 21h
    jc fail
    or dx, dx
    jnz fail
    cmp ax, 63320
    jne fail
    mov ax, 4200h
    xor cx, cx
    xor dx, dx
    int 21h
    jc fail
    mov ah, 3ch
    xor cx, cx
    mov dx, target
    int 21h
    jc fail
    mov [dst], ax
.copy:
    mov bx, [src]
    mov ah, 3fh
    mov cx, 256
    mov dx, buf1
    int 21h
    jc fail
    or ax, ax
    jz .copied
    mov [amount], ax
    mov cx, ax
    mov bx, [dst]
    mov ah, 40h
    int 21h
    jc fail
    cmp ax, [amount]
    jne fail
    jmp .copy
.copied:
    mov bx, [dst]
    mov ah, 3eh
    int 21h
    jc fail
    mov ax, 3d00h
    mov dx, target
    int 21h
    jc fail
    mov [dst], ax
    mov bx, [src]
    mov ax, 4200h
    xor cx, cx
    xor dx, dx
    int 21h
    jc fail
.verify:
    mov bx, [src]
    mov ah, 3fh
    mov cx, 256
    mov dx, buf1
    int 21h
    jc fail
    mov [amount], ax
    mov bx, [dst]
    mov ah, 3fh
    mov cx, 256
    mov dx, buf2
    int 21h
    jc fail
    cmp ax, [amount]
    jne fail
    or ax, ax
    jz success
    mov cx, ax
    mov si, buf1
    mov di, buf2
    cld
    repe cmpsb
    jne fail
    jmp .verify
success:
    mov bx, [src]
    mov ah, 3eh
    int 21h
    jc fail
    mov bx, [dst]
    mov ah, 3eh
    int 21h
    jc fail
    mov dx, good
    mov ah, 09h
    int 21h
    mov ax, 4c00h
    int 21h
fail:
    mov dx, bad
    mov ah, 09h
    int 21h
    mov ax, 4c01h
    int 21h
source db 'KERNFW2A',0
target db 'KERNBOP',0
good db 'KERNBOP copied and verified.',13,10,'$'
bad db 'Kernel copy/readback failed. Check files and free space on C:.',13,10,'$'
src dw 0
dst dw 0
amount dw 0
buf1 times 256 db 0
buf2 times 256 db 0
