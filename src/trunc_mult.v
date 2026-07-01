`default_nettype none

// fixed issue with weighting in the accumulate stage (added shifter maybe change later if its too much area)
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
  localparam H = DataWidth - DropBits;

  // each partial product is one bit in array per column
  reg signed [DataWidth-1:0] partial_products[0:Columns-1];
  // sum of all partial products per row
  reg signed [$clog2(DataWidth):0] sum_products[0:Columns-1];
  // accumulator of all sum_products
  reg signed [OutputSlice:0] accumulate;

  genvar product_column;
  integer a_idx, b_idx;
  // place each partial product bit result into corresponding bit location in partial
  // product array
  // a == y, b == x
  generate
    for (product_column = DropBits; product_column < OutputWidth; product_column++) begin
      always @(*) begin
        partial_products[product_column-DropBits] = '0;
        for (a_idx = 0; a_idx < DataWidth; a_idx++) begin
          for (b_idx = 0; b_idx < DataWidth; b_idx++) begin
            if (a_idx + b_idx == product_column) begin
              partial_products[product_column-DropBits][a_idx] = a[a_idx] & b[b_idx];

              // baugh-wooley inverting of xn-1's (y terms)
              // and inverting of ym-1's (x terms)
              // see fig.3 on the baugh wooley paper
              if (a_idx == DataWidth - 1 && b_idx == DataWidth - 1) begin
                partial_products[product_column-DropBits][a_idx] = a[a_idx] & b[b_idx];
              end else if (a_idx == DataWidth - 1) begin
                partial_products[product_column-DropBits][a_idx] = a[a_idx] & (~b[b_idx]);
              end else if (b_idx == DataWidth - 1) begin
                partial_products[product_column-DropBits][a_idx] = (~a[a_idx]) & b[b_idx];
              end
            end
          end
        end
      end
    end
  endgenerate

  integer col_idx, bit_idx;
  // sum partial product arrays
  always @(*) begin
    for (col_idx = DropBits; col_idx < OutputWidth; col_idx++) begin
      sum_products[col_idx-DropBits] = '0;

      // sum across all bits per partial product array
      for (bit_idx = 0; bit_idx < DataWidth; bit_idx++) begin
        sum_products[col_idx-DropBits] = sum_products[col_idx-DropBits] + partial_products[col_idx-DropBits][bit_idx];
      end

      // extra terms from baugh-wooley
      if (col_idx == OutputWidth - 2) begin
        sum_products[col_idx-DropBits] = sum_products[col_idx-DropBits] + (~a[DataWidth-1]) + (~b[DataWidth-1]);
      end else if (col_idx == DataWidth - 1) begin
        sum_products[col_idx-DropBits] = sum_products[col_idx-DropBits] + a[DataWidth-1] + b[DataWidth-1];
      end

    end
  end

  // partial produts for the error correct IC column
  // separate from above genblk because ran into indexing issues
  reg [DataWidth-1:0] ic_column;
  always @(*) begin
    ic_column = '0;
    for (a_idx = 0; a_idx < DataWidth; a_idx++) begin
      for (b_idx = 0; b_idx < DataWidth; b_idx++) begin
        if (a_idx + b_idx == DropBits - 1) begin
          ic_column[a_idx] = a[a_idx] & b[b_idx];
        end
      end
    end
  end

  // edge ic values are 4 total values (4 bits summed together max at 1 == 4 which needs 2 bits)
  // middle ic values are 11 bit values max value of 11, needs 5 bits to hold max possible
  // "Low error Truncated Multipliers for DSP applications" Garafolo et al.
  reg [2:0] edge_ic;
  reg [4:0] middle_ic;
  always @(*) begin
    edge_ic   = 0;
    middle_ic = 0;
    for (bit_idx = 1; bit_idx <= DataWidth - H; bit_idx++) begin
      if (bit_idx == 1 || bit_idx == 2 || bit_idx == DataWidth - H - 1 || bit_idx == DataWidth - H) begin
        edge_ic = edge_ic + ic_column[bit_idx];
      end else begin
        middle_ic = middle_ic + ic_column[bit_idx];
      end
    end
  end

  // accumulate sum of partial products into final accumulator (and shift to account for column weighting)
  integer product_idx;
  always @(*) begin
    accumulate = '0;
    for (product_idx = DropBits; product_idx < OutputWidth; product_idx++) begin
      if (product_idx == OutputWidth - 1) begin
        accumulate = accumulate + ((sum_products[product_idx-DropBits] + 1'b1) << (product_idx - DropBits + 1));
      end else begin
        accumulate = accumulate + (sum_products[product_idx-DropBits] << (product_idx - DropBits + 1));
      end
    end

    // these shifts values are derived from:
    // "Low error Truncated Multipliers for DSP applications" Garafolo et al.
    accumulate = accumulate + (edge_ic) + (middle_ic << 1);
  end

  assign out = accumulate[OutputSlice:1];

endmodule
