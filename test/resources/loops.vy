
cc: constant(int128) = 12
reward: wei_value


@public
def claim_reward(amount: wei_value):
	num: uint256 = 12
	did_pay: bool = True
	did_pay = not False
	did_pay = False and False and False and False and True
	did_pay = True and False or False and True
	did_pay = True or False
	val: wei_value = amount + amount

@public
def cc(amount: wei_value) -> bool:
	num: uint256 = 12
	if num == 12 or num < 13 or 45 > num:
		num = 14
	did_pay: bool = True
	did_pay = False
	did_pay = False and False and False and False and True
	did_pay = True and False or False and True
	did_pay = True or False
	val: wei_value = amount + amount + (-amount)
	return did_pay
	
@private
def ffi(amount: wei_value, bb: bool) -> wei_value:
	if bb and not True:
		return amount
	else:
		return amount + amount

@private
def loop() -> int128:
	res: int128 = 0
	for i in range(5):
		res = res + i
	return res

@private
def range2() -> int128:
	res: int128
	p: int128 = 20
	for i in range(p, p + 5):
		res += i
	return res

@private
def nested_loop() -> int128:
	res: int128 = 0
	for i in range(5):
		if i == 2:
			break
		if i == 5:
			continue
		for j in range(2):
			res = res + j
	else:
		res = 5
	return res