	.data
STR0:
	.asciiz "neg"                           # literal 0
STR1:
	.asciiz "zero"                          # literal 1
STR2:
	.asciiz "pos"                           # literal 2
STR3:
	.asciiz "cero"                          # literal 3
STR4:
	.asciiz "uno"                           # literal 4
STR5:
	.asciiz "otro"                          # literal 5
STR6:
	.asciiz "true"                          # literal 6
STR7:
	.asciiz "false"                         # literal 7

	.text
	.globl main
	j main                                  # entry jump
	nop
main:
	addi $sp, $sp, -64                      # reservar spills main
	addi $fp, $sp, 64
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
	sw $t8, -40($fp)
	lw $t8, -40($fp)
	li $t9, 0
	xor $t9, $t8, $t9
	sltiu $t2, $t9, 1
	beq $t2, $zero, LTEST8
	j L5
LTEST8:
	lw $t8, -40($fp)
	li $t9, 1
	xor $t9, $t8, $t9
	sltiu $t2, $t9, 1
	beq $t2, $zero, L7
	j L6
L5:
	la $a0, STR3                            # arg0 string
	jal __print_str
	j L4
L6:
	la $a0, STR4                            # arg0 string
	jal __print_str
	j L4
L7:
	la $a0, STR5                            # arg0 string
	jal __print_str
L4:
end_main:
	addi $sp, $sp, 64                       # liberar spills main
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
	la $a0, STR6
	li $v0, 4
	syscall
	j __bool_nl
__bool_false:
	la $a0, STR7
	li $v0, 4
	syscall
__bool_nl:
	li $v0, 11
	li $a0, 10
	syscall
	jr $ra