	.data
STR0:
	.asciiz "[SETUP] Inicializando arreglo people de tamaño 3" # literal 0
STR1:
	.asciiz "Ana"                           # literal 1
STR2:
	.asciiz "[NEW] Creado objeto Person p0 con nombre Ana" # literal 2
STR3:
	.asciiz "[INIT] p0.init completado"     # literal 3
STR4:
	.asciiz "INDEX_OOB"                     # literal 4
STR5:
	.asciiz "[ARRAY] people[0] asignado a Ana" # literal 5
STR6:
	.asciiz "Ben"                           # literal 6
STR7:
	.asciiz "[NEW] Creado objeto Student p1 con nombre Ben y grade 90" # literal 7
STR8:
	.asciiz "[INIT] p1.init completado"     # literal 8
STR9:
	.asciiz "[ARRAY] people[1] asignado a Ben" # literal 9
STR10:
	.asciiz "Cami"                          # literal 10
STR11:
	.asciiz "[NEW] Creado objeto Student p2 con nombre Cami y grade 95" # literal 11
STR12:
	.asciiz "[INIT] p2.init completado"     # literal 12
STR13:
	.asciiz "[ARRAY] people[2] asignado a Cami" # literal 13
STR14:
	.asciiz "[INFO] Comenzando recorrido del arreglo people (for i=0..n, incluye OOB para probar catch)" # literal 14
STR15:
	.asciiz "[TEST] Intentando división por cero para activar catch correspondiente" # literal 15
STR16:
	.asciiz "[FINAL] PRUEBAS DE ARRAYS CHECK" # literal 16
STR17:
	.asciiz "[DONE] Fin del script OK-3"    # literal 17

	.text
	.globl main
	j main                                  # entry jump
	nop
main:
	addi $sp, $sp, -232                     # reservar spills main
	addi $fp, $sp, 232
	li $t9, 3
	move $s1, $t9
	li $t8, 3
	addi $a0, $t8, 1
	sll $a0, $a0, 2
	li $v0, 9
	syscall
	move $t0, $v0
	sw $t8, 0($t0)
	move $s3, $t0
	la $a0, STR0                            # arg0 string
	jal __print_str
	la $a0, STR1                            # arg0 string
	la $t2, STR1
	li $a0, 12
	li $v0, 9
	syscall
	move $t0, $v0                           # obj ptr
	li $t1, 1                               # tag Person
	sw $t1, 0($t0)
	sw $t2, 4($t0)                          # store name ptr
	sw $zero, 8($t0)                        # grade=0
	move $v0, $t0
	move $t0, $v0                           # return value
	move $t8, $t0
	sw $t8, -40($fp)
	la $a0, STR2                            # arg0 string
	jal __print_str
	lw $t8, -40($fp)
	la $a0, STR1                            # arg0 string
	move $a1, $t8                           # arg1
	move $t0, $t8
	lw $t1, 0($t0)                          # load tag
	la $t2, STR1
	sw $t2, 4($t0)                          # set name
	move $v0, $t0                           # return obj
	move $t0, $v0                           # return value
	la $a0, STR3                            # arg0 string
	jal __print_str
	li $t9, 0
	lw $t7, 0($s3)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB1
	j OOBOK2
OOB1:
	la $a0, STR4
	jal __print_str
OOBOK2:
	li $t9, 0
	lw $t7, -40($fp)
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $s3
	sw $t7, 0($t6)
	la $a0, STR5                            # arg0 string
	jal __print_str
	la $a0, STR6                            # arg0 string
	li $a1, 90                              # arg1 int
	la $t2, STR6
	li $t3, 90
	li $a0, 12
	li $v0, 9
	syscall
	move $t0, $v0                           # obj ptr
	li $t1, 2                               # tag Student
	sw $t1, 0($t0)
	sw $t2, 4($t0)                          # store name ptr
	sw $t3, 8($t0)                          # store grade
	move $v0, $t0
	move $t1, $v0                           # return value
	move $t8, $t1
	sw $t8, -92($fp)
	la $a0, STR7                            # arg0 string
	jal __print_str
	lw $t8, -92($fp)
	la $a0, STR6                            # arg0 string
	li $a1, 90                              # arg1 int
	move $a2, $t8                           # arg2
	move $t0, $t8
	lw $t1, 0($t0)                          # load tag
	la $t2, STR6
	sw $t2, 4($t0)                          # set name
	li $t3, 90
	sw $t3, 8($t0)                          # set grade
	move $v0, $t0                           # return obj
	move $t1, $v0                           # return value
	la $a0, STR8                            # arg0 string
	jal __print_str
	li $t9, 1
	lw $t7, 0($s3)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB3
	j OOBOK4
OOB3:
	la $a0, STR4
	jal __print_str
OOBOK4:
	li $t9, 1
	lw $t7, -92($fp)
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $s3
	sw $t7, 0($t6)
	la $a0, STR9                            # arg0 string
	jal __print_str
	la $a0, STR10                           # arg0 string
	li $a1, 95                              # arg1 int
	la $t2, STR10
	li $t3, 95
	li $a0, 12
	li $v0, 9
	syscall
	move $t0, $v0                           # obj ptr
	li $t1, 2                               # tag Student
	sw $t1, 0($t0)
	sw $t2, 4($t0)                          # store name ptr
	sw $t3, 8($t0)                          # store grade
	move $v0, $t0
	move $t2, $v0                           # return value
	move $t8, $t2
	sw $t8, -152($fp)
	la $a0, STR11                           # arg0 string
	jal __print_str
	lw $t8, -152($fp)
	la $a0, STR10                           # arg0 string
	li $a1, 95                              # arg1 int
	move $a2, $t8                           # arg2
	move $t0, $t8
	lw $t1, 0($t0)                          # load tag
	la $t2, STR10
	sw $t2, 4($t0)                          # set name
	li $t3, 95
	sw $t3, 8($t0)                          # set grade
	move $v0, $t0                           # return obj
	move $t2, $v0                           # return value
	la $a0, STR12                           # arg0 string
	jal __print_str
	li $t9, 2
	lw $t7, 0($s3)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB5
	j OOBOK6
OOB5:
	la $a0, STR4
	jal __print_str
OOBOK6:
	li $t9, 2
	lw $t7, -152($fp)
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $s3
	sw $t7, 0($t6)
	la $a0, STR13                           # arg0 string
	jal __print_str
	la $a0, STR14                           # arg0 string
	jal __print_str
	li $t9, 0
	move $t8, $t9
	sw $t8, -200($fp)
L0:
	lw $t8, -200($fp)
	slt $t9, $s1, $t8
	xori $t3, $t9, 1
	beq $t3, $zero, L2
	lw $t9, -200($fp)
	lw $t7, 0($s3)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB7
	j OOBOK8
OOB7:
	la $a0, STR4
	jal __print_str
OOBOK8:
	lw $t9, -200($fp)
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $s3
	lw $t3, 0($t6)
	move $a0, $t3                           # arg0
	move $t0, $t3
	lw $t1, 0($t0)                          # tag
	lw $t2, 4($t0)                          # name ptr
	move $a0, $t2
	jal __print_str                         # print name
	li $t3, 2
	bne $t1, $t3, GREET_DONE10
	lw $t4, 8($t0)                          # grade
	move $a0, $t4
	jal __print_int                         # print grade
GREET_DONE10:
	move $v0, $zero
	move $t4, $v0                           # return value
L1:
	lw $t8, -200($fp)
	li $t9, 1
	add $t3, $t8, $t9
	move $t8, $t3
	sw $t8, -200($fp)
	j L0
L2:
	la $a0, STR15                           # arg0 string
	jal __print_str
	li $t8, 10
	li $t9, 0
	beq $t9, $zero, DIV_Z12
	div $t8, $t9
	mflo $t3
	j DIV_OK11
DIV_Z12:
	move $t3, $zero
DIV_OK11:
	move $t8, $t3
	sw $t8, -220($fp)
	lw $t8, -220($fp)
	move $a0, $t8                           # arg0
	jal __print_int
	la $a0, STR16                           # arg0 string
	jal __print_str
	la $a0, STR17                           # arg0 string
	jal __print_str
end_main:
	addi $sp, $sp, 232                      # liberar spills main
	li $v0, 10                              # exit syscall
	syscall
__print_int:	# runtime print integer
	li $v0, 1
	syscall
	li $v0, 11
	li $a0, 10
	syscall
	jr $ra
__print_str:	# runtime print string
	li $v0, 4
	syscall
	li $v0, 11
	li $a0, 10
	syscall
	jr $ra