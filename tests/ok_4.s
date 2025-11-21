	.data
STR0:
	.asciiz "neg"                           # literal 0
STR1:
	.asciiz "zero"                          # literal 1
STR2:
	.asciiz "pos"                           # literal 2
STR3:
	.asciiz "INDEX_OOB"                     # literal 3
STR4:
	.asciiz "cero"                          # literal 4
STR5:
	.asciiz "uno"                           # literal 5
STR6:
	.asciiz "otro"                          # literal 6
STR7:
	.asciiz "true"                          # literal 7
STR8:
	.asciiz "false"                         # literal 8

	.text
	.globl main
	j main                                  # entry jump
	nop
main:
	addi $sp, $sp, -264                     # reservar spills main
	addi $fp, $sp, 264
	li $t9, 5
	move $s1, $t9
	li $t9, 0
	slt $t0, $s1, $t9
	beq $t0, $zero, L0
	la $a0, STR0                            # arg0 string
	jal __print_str
	j L1
L0:
	li $t9, 0
	xor $t9, $s1, $t9
	sltiu $t1, $t9, 1
	beq $t1, $zero, L2
	la $a0, STR1                            # arg0 string
	jal __print_str
	j L3
L2:
	la $a0, STR2                            # arg0 string
	jal __print_str
L3:
L1:
	li $t9, 0
	move $t8, $t9
	sw $t8, -244($fp)
L4:
	lw $t8, -244($fp)
	li $t9, 3
	slt $t2, $t8, $t9
	beq $t2, $zero, L5
	lw $t8, -244($fp)
	move $a0, $t8                           # arg0
	jal __print_int
	lw $t8, -244($fp)
	li $t9, 1
	add $t3, $t8, $t9
	move $t8, $t3
	sw $t8, -244($fp)
	j L4
L5:
	li $t9, 0
	move $t8, $t9
	sw $t8, -72($fp)
L6:
	lw $t8, -72($fp)
	move $a0, $t8                           # arg0
	jal __print_int
	lw $t8, -72($fp)
	li $t9, 1
	add $t3, $t8, $t9
	move $t8, $t3
	sw $t8, -72($fp)
L7:
	lw $t8, -72($fp)
	li $t9, 2
	slt $t3, $t8, $t9
	beq $t3, $zero, L8
	j L6
L8:
	li $t9, 0
	move $t8, $t9
	sw $t8, -104($fp)
L9:
	lw $t8, -104($fp)
	li $t9, 2
	slt $t4, $t8, $t9
	beq $t4, $zero, L11
	lw $t8, -104($fp)
	move $a0, $t8                           # arg0
	jal __print_int
L10:
	lw $t8, -104($fp)
	li $t9, 1
	add $t4, $t8, $t9
	move $t8, $t4
	sw $t8, -104($fp)
	j L9
L11:
	li $t8, 3
	addi $a0, $t8, 1
	sll $a0, $a0, 2
	li $v0, 9
	syscall
	move $t4, $v0
	sw $t8, 0($t4)
	move $t8, $t4
	sw $t8, -180($fp)
	lw $t8, -180($fp)
	li $t9, 0
	lw $t7, 0($t8)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB1
	j OOBOK2
OOB1:
	la $a0, STR3
	jal __print_str
OOBOK2:
	lw $t8, -180($fp)
	li $t9, 0
	li $t7, 10
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $t8
	sw $t7, 0($t6)
	lw $t8, -180($fp)
	li $t9, 1
	lw $t7, 0($t8)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB3
	j OOBOK4
OOB3:
	la $a0, STR3
	jal __print_str
OOBOK4:
	lw $t8, -180($fp)
	li $t9, 1
	li $t7, 20
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $t8
	sw $t7, 0($t6)
	lw $t8, -180($fp)
	li $t9, 2
	lw $t7, 0($t8)
	slt $t6, $t9, $t7
	beq $t6, $zero, OOB5
	j OOBOK6
OOB5:
	la $a0, STR3
	jal __print_str
OOBOK6:
	lw $t8, -180($fp)
	li $t9, 2
	li $t7, 30
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $t8
	sw $t7, 0($t6)
	li $t9, 0
	move $t8, $t9
	sw $t8, -200($fp)
	lw $t8, -180($fp)
	lw $t4, 0($t8)
L12:
	lw $t8, -200($fp)
	slt $t5, $t8, $t4
	beq $t5, $zero, L13
	lw $t8, -180($fp)
	lw $t9, -200($fp)
	sll $t6, $t9, 2
	addi $t6, $t6, 4
	add $t6, $t6, $t8
	lw $t6, 0($t6)
	move $t8, $t6
	sw $t8, -192($fp)
	lw $t8, -192($fp)
	move $a0, $t8                           # arg0
	jal __print_int
L14:
	lw $t8, -200($fp)
	li $t9, 1
	add $t7, $t8, $t9
	move $t8, $t7
	sw $t8, -200($fp)
	j L12
L13:
	li $t9, 0
	move $t8, $t9
L15:
	li $t9, 5
	slt $t7, $t8, $t9
	beq $t7, $zero, L16
	li $t9, 1
	add $t6, $t8, $t9
	move $t8, $t6
	li $t9, 2
	xor $t9, $t8, $t9
	sltiu $t6, $t9, 1
	beq $t6, $zero, L17
	j L15
L17:
	li $t9, 4
	xor $t9, $t8, $t9
	sltiu $t5, $t9, 1
	beq $t5, $zero, L18
	j L16
L18:
	move $a0, $t8                           # arg0
	jal __print_int
	j L15
L16:
	lw $t8, -244($fp)
	li $t9, 0
	xor $t9, $t8, $t9
	sltiu $t4, $t9, 1
	beq $t4, $zero, LTEST23
	j L20
LTEST23:
	lw $t8, -244($fp)
	li $t9, 1
	xor $t9, $t8, $t9
	sltiu $t4, $t9, 1
	beq $t4, $zero, L22
	j L21
L20:
	la $a0, STR4                            # arg0 string
	jal __print_str
L21:
	la $a0, STR5                            # arg0 string
	jal __print_str
L22:
	la $a0, STR6                            # arg0 string
	jal __print_str
L19:
end_main:
	addi $sp, $sp, 264                      # liberar spills main
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
__print_bool:
	beq $a0, $zero, __bool_false
	la $a0, STR7
	li $v0, 4
	syscall
	j __bool_nl
__bool_false:
	la $a0, STR8
	li $v0, 4
	syscall
__bool_nl:
	li $v0, 11
	li $a0, 10
	syscall
	jr $ra