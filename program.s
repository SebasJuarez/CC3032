	.data

	.text
main:
	addi $sp, $sp, -200                     # reservar spills main
	addi $fp, $sp, 200
	li $t9, 3
	move $s1, $t9
	# UNSUPPORTED newarr
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	move $s3, $t0
	move $a0, $s4                           # param (simple)
	jal Person.new
	move $t0, $v0                           # return value
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	move $s7, $t0
	move $a0, $s4                           # param (simple)
	move $a0, $s7                           # param (simple)
	jal invoke.init
	move $t0, $v0                           # return value
	# UNSUPPORTED idxchk
	# UNSUPPORTED aload
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	# UNSUPPORTED astore
	lw $t8, -48($fp)
	move $a0, $t8                           # param (simple)
	li $t8, 90
	move $a0, $t8                           # param (simple)
	jal Student.new
	move $t1, $v0                           # return value
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	move $t8, $t1
	sw $t8, -68($fp)
	lw $t8, -48($fp)
	move $a0, $t8                           # param (simple)
	li $t8, 90
	move $a0, $t8                           # param (simple)
	lw $t8, -68($fp)
	move $a0, $t8                           # param (simple)
	jal invoke.init
	move $t1, $v0                           # return value
	# UNSUPPORTED idxchk
	# UNSUPPORTED aload
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	# UNSUPPORTED astore
	lw $t8, -96($fp)
	move $a0, $t8                           # param (simple)
	li $t8, 95
	move $a0, $t8                           # param (simple)
	jal Student.new
	move $t2, $v0                           # return value
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	move $t8, $t2
	sw $t8, -128($fp)
	lw $t8, -96($fp)
	move $a0, $t8                           # param (simple)
	li $t8, 95
	move $a0, $t8                           # param (simple)
	lw $t8, -128($fp)
	move $a0, $t8                           # param (simple)
	jal invoke.init
	move $t2, $v0                           # return value
	# UNSUPPORTED idxchk
	# UNSUPPORTED aload
	# UNSUPPORTED incref
	# UNSUPPORTED decref
	# UNSUPPORTED astore
	li $t9, 0
	move $t8, $t9
	sw $t8, -168($fp)
L0:
	lw $t8, -168($fp)
	lw $t9, -144($fp)
	slt $t9, $s1, $t8
	xori $t3, $t9, 1
	beq $t3, $zero, L2
	# UNSUPPORTED idxchk
	# UNSUPPORTED aload
	move $a0, $t3                           # param (simple)
	jal invoke.greet
	move $t4, $v0                           # return value
L1:
	lw $t8, -168($fp)
	li $t9, 1
	add $t3, $t8, $t9
	move $t8, $t3
	sw $t8, -168($fp)
	j L0
L2:
	li $t8, 10
	li $t9, 0
	beq $t9, $zero, DIV_Z2
	div $t8, $t9
	mflo $t3
	j DIV_OK1
DIV_Z2:
	move $t3, $zero
DIV_OK1:
	move $t8, $t3
	sw $t8, -184($fp)
	lw $t8, -184($fp)
	move $a0, $t8                           # param (simple)
	jal __print_int
	lw $t8, -192($fp)
	move $a0, $t8                           # param (simple)
	jal __print_int
end_main:
	addi $sp, $sp, 200                      # liberar spills main
	li $v0, 10                              # exit syscall
	syscall
__print_int:	# runtime print integer
	li $v0, 1
	syscall
	jr $ra
Person.new:	# external stub
	move $v0, $zero
	jr $ra
invoke.init:	# external stub
	move $v0, $zero
	jr $ra
Student.new:	# external stub
	move $v0, $zero
	jr $ra
invoke.greet:	# external stub
	move $v0, $zero
	jr $ra