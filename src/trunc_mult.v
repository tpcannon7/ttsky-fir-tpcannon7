`default_nettype none

module trunc_mult #(
    parameter DataWidth   = 16,
    parameter OutputSlice = 16
) (
    input wire signed [DataWidth-1:0] a,
    input wire signed [DataWidth-1:0] b,

    output wire signed [OutputSlice-1:0] out
);

  localparam OutputWidth = DataWidth * DataWidth;

  genvar cols;
  integer i, j;
  generate
    for (cols = OutputSlice; cols < OutputWidth; cols++) begin
      always @(*) begin
        for (i = 0; i < DataWidth; i++) begin
          for (j = 0; j < DataWidth; j++) begin

          end
        end
      end
    end

  endgenerate

endmodule
