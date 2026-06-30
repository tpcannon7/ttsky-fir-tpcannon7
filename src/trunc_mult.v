`default_nettype none

// fixed issue with weighting in the accumulate stage (added shifteer maybe change later if its too much area)
// added shitty 2's complement fix for negative numbers (we're changing this)

module trunc_mult #(
    parameter DataWidth = 16,
    parameter DropBits  = 15   // this is our dropped LSP bits
) (
    input wire signed [DataWidth-1:0] a,
    input wire signed [DataWidth-1:0] b,

    output wire signed [((DataWidth*2)-DropBits)-1:0] out
);

  localparam OutputWidth = DataWidth * 2;
  localparam OutputSlice = (DataWidth * 2) - DropBits;
  localparam Columns = OutputWidth - DropBits;

  // sum of all partial products per row
  reg signed [$clog2(DataWidth):0] sum_products[0:Columns-1];

  // each partial product is one bit in array per column
  reg signed [DataWidth-1:0] partial_products[0:Columns-1];

  reg signed [OutputSlice-1:0] accumulate;

  genvar product_column;
  integer i, j;
  // place each partial product bit result into corresponding bit location in partial
  // product array
  generate
    for (product_column = DropBits; product_column < OutputWidth; product_column++) begin
      always @(*) begin
        partial_products[product_column-DropBits] = '0;
        for (i = 0; i < DataWidth; i++) begin
          for (j = 0; j < DataWidth; j++) begin
            if (i + j == product_column) begin
              partial_products[product_column-DropBits][i] = a[i] & b[j];
            end
          end
        end
      end
    end
  endgenerate

  // sum partial product arrays
  always @(*) begin
    for (i = DropBits; i < OutputWidth; i++) begin
      sum_products[i-DropBits] = '0;
      for (j = 0; j < DataWidth; j++) begin
        sum_products[i-DropBits] = sum_products[i-DropBits] + partial_products[i-DropBits][j];
      end
    end
  end

  // accumulate sum of partial products into final accumulator (and shift to account for column weighting)
  always @(*) begin
    accumulate = '0;
    for (i = DropBits; i < OutputWidth; i++) begin
      accumulate = accumulate + (sum_products[i-DropBits] << (i - DropBits));
    end
  end

  assign out = accumulate;

endmodule
