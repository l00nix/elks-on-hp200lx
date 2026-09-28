; HP 200LX pre-handoff diagnostic. NASM, 8086 instruction set.
; GPL-2.0-or-later. Run HPSNAP > HPFW.TXT under DOS.
; No hardware state changes beyond restoring the indexed-register selector.
bits 16
cpu 8086
org 100h
start:
    push cs
    pop ds
    mov dx, title
    call puts
    mov ax, 4dd4h
    int 15h
    cmp bx, 4850h
    jne wrong
    cmp cx, 0102h
    jne wrong
    mov ax, dx
    mov dx, model
    call puts
    call hexword
    call newline
    cmp ah, 2
    jne wrong

    xor ax, ax
    mov es, ax
    mov si, vectors
.vec:
    xor ax, ax
    mov al, [si]
    inc si
    cmp al, 0ffh
    je .table
    push ax
    mov dx, intlabel
    call puts
    call hexword
    pop bx
    shl bx, 1
    shl bx, 1
    call farpointer
    jmp .vec
.table:
    mov ax, 9000h
    mov es, ax
    mov bx, 0f7ach
    mov cx, 16
.entry:
    mov dx, tablelabel
    call puts
    mov ax, bx
    call hexword
    call farpointer
    add bx, 4
    loop .entry
    mov si, indices
.reg:
    xor ax, ax
    mov al, [si]
    inc si
    cmp al, 0ffh
    je .pic
    mov dx, indexlabel
    call puts
    call hexword
    mov bl, al
    pushf
    cli
    in al, 22h
    mov bh, al
    mov al, bl
    out 22h, al
    in al, 23h
    mov bl, al
    mov al, bh
    out 22h, al
    popf
    mov dx, equal
    call puts
    xor ax, ax
    mov al, bl
    call hexword
    call newline
    jmp .reg
.pic:
    mov dx, piclabel
    call puts
    xor ax, ax
    in al, 21h
    call hexword
    call newline
    mov dx, ppilabel
    call puts
    xor ax, ax
    in al, 61h
    call hexword
    call newline
    mov ax, 0040h
    mov es, ax
    mov dx, statelabel
    call puts
    xor ax, ax
    mov al, [es:0095h]
    call hexword
    call newline
    mov ax, 4c00h
    int 21h
wrong:
    mov dx, badmodel
    call puts
    mov ax, 4c01h
    int 21h

farpointer:
    mov dx, equal
    call puts
    mov ax, [es:bx+2]
    call hexword
    mov dx, colon
    call puts
    mov ax, [es:bx]
    call hexword
    call newline
    ret
hexword:
    push ax
    push bx
    push cx
    push dx
    mov bx, ax
    mov cx, 4
.digit:
    push cx
    mov cl, 4
    rol bx, cl
    mov dl, bl
    and dl, 0fh
    add dl, '0'
    cmp dl, '9'
    jbe .print
    add dl, 7
.print:
    mov ah, 02h
    int 21h
    pop cx
    loop .digit
    pop dx
    pop cx
    pop bx
    pop ax
    ret
newline:
    push dx
    mov dx, crlf
    call puts
    pop dx
    ret
puts:
    push ax
    mov ah, 09h
    int 21h
    pop ax
    ret

title db 'HP200LX FW1 DOS snapshot',13,10,'$'
model db 'MODEL/REV DX=$'
intlabel db 'INT $'
tablelabel db 'IRQ2 TABLE 9000:$'
indexlabel db 'HORNET INDEX $'
piclabel db 'PIC21=$'
ppilabel db 'PPI61=$'
statelabel db 'BIOS T1_STATE=$'
badmodel db 'Not an HP 200LX; stopped.',13,10,'$'
equal db ' = $'
colon db ':$'
crlf db 13,10,'$'
vectors db 02h,06h,08h,09h,0ah,10h,13h,15h,16h,1ch,0ffh
indices db 18h,19h,1ah,0e8h,0e7h,0ffh
