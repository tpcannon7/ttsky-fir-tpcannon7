`default_nettype none

module trunc_mult #(
    parameter DataWidth = 12,
    parameter DropBits  = 8    // this is our dropped LSP bits
) (
    input wire signed [DataWidth-1:0] a,
    input wire signed [DataWidth-1:0] b,

    output wire signed [((DataWidth*2)-DropBits)-1:0] out
);

  localparam OutputWidth = DataWidth * 2;
  localparam OutputSlice = (DataWidth * 2) - DropBits;
  localparam Columns = OutputWidth - DropBits;
  localparam H = DataWidth - DropBits;

  localparam EdgeICWidth = 3;
  localparam MiddleICTermAmt = DataWidth - H - 4;
  localparam MiddleICWidth = (MiddleICTermAmt <= 0) ? 1 : $clog2(MiddleICTermAmt + 1);

  // each partial product is one bit in array per column
  reg [DataWidth-1:0] partial_products[0:Columns-1];
  // sum of all partial products per row
  reg [$clog2(DataWidth):0] sum_products[0:Columns-1];
  // accumulator of all sum_products
  reg [OutputSlice:0] accumulate;

  genvar product_column;
  integer a_idx, b_idx;
  // place each partial product bit result into corresponding bit location in partial
  // product array
  // a == y, b == x
  generate
    for (product_column = DropBits; product_column < OutputWidth; product_column++) begin : gen_pps
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
  always @(*) begin : comb_sum_partial_products
    for (col_idx = DropBits; col_idx < OutputWidth; col_idx++) begin
      sum_products[col_idx-DropBits] = '0;

      // sum across all bits per partial product array
      for (bit_idx = 0; bit_idx < DataWidth; bit_idx++) begin
        sum_products[col_idx-DropBits] = sum_products[col_idx-DropBits] +
            {{($clog2(DataWidth) - 1) {1'b0}}, partial_products[col_idx-DropBits][bit_idx]};
      end

      // extra terms from baugh-wooley
      if (col_idx == OutputWidth - 2) begin
        sum_products[col_idx-DropBits] = sum_products[col_idx-DropBits] +
            {{($clog2(DataWidth) - 1) {1'b0}}, (~a[DataWidth-1])} +
            {{($clog2(DataWidth) - 1) {1'b0}}, (~b[DataWidth-1])};
      end else if (col_idx == DataWidth - 1) begin
        sum_products[col_idx-DropBits] = sum_products[col_idx-DropBits] +
            {{($clog2(DataWidth) - 1) {1'b0}}, a[DataWidth-1]} +
            {{($clog2(DataWidth) - 1) {1'b0}}, b[DataWidth-1]};
      end

    end
  end

  // partial produts for the error correct IC column
  // separate from above genblk because ran into indexing issues
  // note: this ic column indexing is only valid for DropBits < DataWidth
  // the baugh wooley signed correction + IC error correction will fail
  // if you drop half the bits (DataWidth amount or more) because h=0 and beyond
  // is a special case and is not supported
  reg [DataWidth-1:0] ic_column;
  always @(*) begin : comb_ic_column_partial_product
    ic_column = '0;
    for (a_idx = 0; a_idx < DataWidth; a_idx++) begin
      for (b_idx = 0; b_idx < DataWidth; b_idx++) begin
        if (a_idx + b_idx == DropBits - 1) begin
          ic_column[a_idx] = a[a_idx] & b[b_idx];
        end
      end
    end
  end

  // edge ic values are 4 total values (4 bits summed together 1+1+1+1 = 4 which needs 3 bits)
  // edge ic is: i = 1,2,n-h-1, n-h
  // middle ic: 2 < i < n - h - 1
  // subtract all by 1 to use base 0 indexing
  // middle ic values are 11 bit values max value of 11 (1+1+1+1...+1=11), needs 4 bits to hold max possible
  // "Low error Truncated Multipliers for DSP applications" Garofalo et al.
  reg [  EdgeICWidth-1:0] edge_ic;
  reg [MiddleICWidth-1:0] middle_ic;
  always @(*) begin : comb_middle_edge_error_ic_terms
    edge_ic   = 0;
    middle_ic = 0;
    for (bit_idx = 0; bit_idx < DataWidth - H; bit_idx++) begin
      if (bit_idx == 0 || bit_idx == 1 || bit_idx == DataWidth - H - 2 || bit_idx == DataWidth - H - 1) begin
        edge_ic = edge_ic + {{{(EdgeICWidth - 1) {1'b0}}, ic_column[bit_idx]}};
      end else begin
        middle_ic = middle_ic + {{(MiddleICWidth - 1) {1'b0}}, ic_column[bit_idx]};
      end
    end
  end

  // accumulate sum of partial products into final accumulator (and shift to account for column weighting)
  integer product_idx;
  always @(*) begin : comb_accumulate_sum_products
    accumulate = '0;
    for (product_idx = DropBits; product_idx < OutputWidth; product_idx++) begin
      // "1" term added in the final bit column sum
      if (product_idx == OutputWidth - 1) begin
        accumulate = accumulate +
            (({{{OutputWidth - DropBits - $clog2(DataWidth)} {1'b0}},
               sum_products[product_idx-DropBits]} + 1'b1) << (product_idx - DropBits + 1));
      end else begin
        accumulate = accumulate +
            ({{{OutputWidth - DropBits - $clog2(DataWidth)} {1'b0}},
              sum_products[product_idx-DropBits]} << (product_idx - DropBits + 1));
      end
    end
    // these shifts values are derived from:
    // "Low error Truncated Multipliers for DSP applications" Garofalo et al.
    accumulate = accumulate + {{(OutputSlice + 1 - EdgeICWidth){1'b0}},   edge_ic} +
                          ({{{(OutputSlice + 1 - MiddleICWidth){1'b0}}, middle_ic}} << 1);
  end

  assign out = accumulate[OutputSlice:1];

endmodule

`default_nettype wire
