	.data

	.text
fact:
	addi $sp, $sp, -8                       # reservar frame 0+save
	sw $fp, 0($sp)
	sw $ra, 4($sp)
	addi $fp, $sp, 8
	move $s0, $a0                           # param n:integer
	li $t9, 1
	slt $s3, $t9, $s2
	xori $t0, $s3, 1
	beq $t0, $zero, L0
	li $t8, 1
	move $v0, $t8
	lw $fp, 0($sp)
	lw $ra, 4($sp)
	addi $sp, $sp, 8
	jr $ra
L0:
	li $t9, 1
	sub $t1, $s2, $t9
	move $a0, $t1                           # arg0
	jal fact
	move $t1, $v0                           # return value
	mul $t2, $s2, $t1
	move $v0, $t2
	lw $fp, 0($sp)
	lw $ra, 4($sp)
	addi $sp, $sp, 8
	jr $ra
end_fact:
	lw $fp, 0($sp)
	lw $ra, 4($sp)
	addi $sp, $sp, 8
	jr $ra
suma:
	addi $sp, $sp, -8                       # reservar frame 0+save
	sw $fp, 0($sp)
	sw $ra, 4($sp)
	addi $fp, $sp, 8
	move $s0, $a0                           # param a:integer
	move $s1, $a1                           # param b:integer
	add $t0, $s2, $s3
	move $v0, $t0
	lw $fp, 0($sp)
	lw $ra, 4($sp)
	addi $sp, $sp, 8
	jr $ra
end_suma:
	lw $fp, 0($sp)
	lw $ra, 4($sp)
	addi $sp, $sp, 8
	jr $ra
main:
	addi $sp, $sp, -16                      # reservar spills main
	addi $fp, $sp, 16
	li $t8, 3
	li $t8, 4
	move $a0, $t8                           # arg0
	move $a1, $t8                           # arg1
	jal suma
	move $t0, $v0                           # return value
	move $s4, $t0
	li $t8, 5
	move $a0, $t8                           # arg0
	jal fact
	move $t0, $v0                           # return value
	move $t8, $t0
	sw $t8, -12($fp)
	move $a0, $s4                           # arg0
	jal __print_int
	lw $t8, -12($fp)
	move $a0, $t8                           # arg0
	jal __print_int
end_main:
	addi $sp, $sp, 16                       # liberar spills main
	li $v0, 10                              # exit syscall
	syscall
__print_int:	# runtime print integer
	li $v0, 1
	syscall
	jr $ra
__print_str:	# runtime print string
	li $v0, 4
	syscall
	jr $ra