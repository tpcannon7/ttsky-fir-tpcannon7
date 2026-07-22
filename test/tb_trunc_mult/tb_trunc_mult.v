`default_nettype none `timescale 1ns / 1ps

module tb_trunc_mult #(
    parameter DataWidth = 12
) (
    input wire signed [DataWidth-1:0] a,
    input wire signed [DataWidth-1:0] b,

    output wire signed [(DataWidth*2)-1:0] golden_ref,
    output wire signed [(DataWidth*2)-1:0] trunc_out [0:11]
);

  assign golden_ref = a * b;

  genvar drop_bits;
  generate
    for (drop_bits = 0; drop_bits < DataWidth; drop_bits++) begin
      wire signed [(DataWidth*2)-drop_bits-1:0] out;
      assign trunc_out[drop_bits] = out;
      trunc_mult #(
          .DropBits(drop_bits)
      ) mult (
          .a  (a),
          .b  (b),
          .out(out)
      );
    end
  endgenerate

endmodule
