	.data
STR0:
	.asciiz "true"                          # literal 0
STR1:
	.asciiz "false"                         # literal 1

	.text
	.globl main
	j main                                  # entry jump
	nop
main:
	addi $sp, $sp, -24                      # reservar spills main
	addi $fp, $sp, 24
	move $s0, $t0
	move $s2, $s1
	move $a0, $s0                           # arg0
	jal __print_int
	move $a0, $s2                           # arg0
	jal __print_int
	move $a0, $t0                           # arg0
	jal __print_bool
	move $a0, $s1                           # arg0
	jal __print_bool
	li $t9, 5
	move $s7, $t9
	li $t9, 10
	slt $t1, $s7, $t9
	move $a0, $t1                           # arg0
	jal __print_int
	li $t9, 5
	xor $t9, $s7, $t9
	sltiu $t1, $t9, 1
	move $a0, $t1                           # arg0
	jal __print_int
	li $t9, 10
	slt $t1, $t9, $s7
	move $a0, $t1                           # arg0
	jal __print_int
end_main:
	addi $sp, $sp, 24                       # liberar spills main
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
	la $a0, STR0
	li $v0, 4
	syscall
	j __bool_nl
__bool_false:
	la $a0, STR1
	li $v0, 4
	syscall
__bool_nl:
	li $v0, 11
	li $a0, 10
	syscall
	jr $ra
__print_bool:	# external stub
	move $v0, $zero
	jr $ra