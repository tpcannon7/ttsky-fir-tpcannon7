`default_nettype none
// reference 12-bit signed multiply (assign p = a * b) for sky130A synthesis comparison
module baseline_mult #(
    parameter DataWidth = 12
) (
    input  wire signed [  DataWidth-1:0] a,
    input  wire signed [  DataWidth-1:0] b,
    output wire signed [DataWidth*2-1:0] p
);
  assign p = a * b;
endmodule

`default_nettype wire
