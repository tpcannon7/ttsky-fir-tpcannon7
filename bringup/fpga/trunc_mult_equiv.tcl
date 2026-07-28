yosys read_verilog gw5a/src/trunc_mult.v
yosys rename trunc_mult gold
yosys read_verilog gw5a/src/new_trunc_mult.v
yosys rename new_trunc_mult gate

yosys proc
yosys memory
yosys opt

# build equivalence checking design
yosys equiv_make gold gate equiv
yosys prep -top equiv

# prove equivalence
yosys equiv_simple
yosys equiv_status -assert
