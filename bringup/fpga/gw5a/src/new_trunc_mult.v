`default_nettype none

module new_trunc_mult #(
    parameter DataWidth = 12,
    parameter DropBits  = 8    // this is our dropped LSP bits
) (
    input wire signed [DataWidth-1:0] a,
    input wire signed [DataWidth-1:0] b,

    output wire signed [((DataWidth*2)-DropBits)-1:0] out
)  /*synthesis syn_dspstyle="logic" */;

  localparam OutputWidth = DataWidth * 2;
  localparam OutputSlice = (DataWidth * 2) - DropBits;
  localparam Columns = OutputWidth - DropBits;
  localparam H = DataWidth - DropBits;

  localparam EdgeICWidth = 3;
  localparam MiddleICTermAmt = DataWidth - H - 4;
  localparam MiddleICWidth = (MiddleICTermAmt <= 0) ? 1 : $clog2(MiddleICTermAmt + 1);

  // ----------------------------------------------------------------
  // Step 1: N x N partial products with Baugh-Wooley inversions
  // ----------------------------------------------------------------
  wire pp[0:DataWidth-1][0:DataWidth-1];
  genvar i, j;
  generate
    for (i = 0; i < DataWidth; i++) begin : pp_row
      for (j = 0; j < DataWidth; j++) begin : pp_bit
        if (i == DataWidth - 1 && j == DataWidth - 1) begin
          assign pp[i][j] = a[i] & b[j];
        end else if (i == DataWidth - 1) begin
          assign pp[i][j] = a[i] & (~b[j]);
        end else if (j == DataWidth - 1) begin
          assign pp[i][j] = (~a[i]) & b[j];
        end else begin
          assign pp[i][j] = a[i] & b[j];
        end
      end
    end
  endgenerate

  // ----------------------------------------------------------------
  // Step 2: sum partial products by column (popcount per column)
  // Each column c = i + j, pp[i][j] contributes to column c
  // We only care about columns DropBits .. OutputWidth-1
  // ----------------------------------------------------------------
  localparam SumWidth = $clog2(DataWidth) + 1;  // enough for popcount of 12 bits

  // collect which pp bits belong to each column (we care about columns 8..23)
  wire [DataWidth-1:0] col_pp[0:Columns-1];  // up to 12 bits per column
  genvar c;
  generate
    for (c = DropBits; c < OutputWidth; c++) begin : col_assign
      localparam col_idx = c - DropBits;
      for (i = 0; i < DataWidth; i++) begin : col_bit
        localparam jj = c - i;
        if (jj >= 0 && jj < DataWidth) begin
          assign col_pp[col_idx][i] = pp[i][jj];
        end else begin
          assign col_pp[col_idx][i] = 1'b0;
        end
      end
    end
  endgenerate

  // ----------------------------------------------------------------
  // Step 3: popcount per column + Baugh-Wooley correction terms
  // ----------------------------------------------------------------
  function [SumWidth-1:0] popcount;
    input [DataWidth-1:0] bits;
    integer k;
    begin
      popcount = 0;
      for (k = 0; k < DataWidth; k = k + 1) popcount = popcount + {{SumWidth - 1{1'b0}}, bits[k]};
    end
  endfunction

  wire [SumWidth-1:0] col_sum[0:Columns-1];
  generate
    for (c = DropBits; c < OutputWidth; c++) begin : col_sum_gen
      localparam col_idx = c - DropBits;
      wire [SumWidth-1:0] base_sum = popcount(col_pp[col_idx]);
      // Baugh-Wooley correction terms
      if (c == OutputWidth - 2) begin  // column 2N-2
        assign col_sum[col_idx] = base_sum
          + {{SumWidth-1{1'b0}}, (~a[DataWidth-1])}
          + {{SumWidth-1{1'b0}}, (~b[DataWidth-1])};
      end else if (c == DataWidth - 1) begin  // column N-1
        assign col_sum[col_idx] = base_sum
          + {{SumWidth-1{1'b0}}, a[DataWidth-1]}
          + {{SumWidth-1{1'b0}}, b[DataWidth-1]};
      end else begin
        assign col_sum[col_idx] = base_sum;
      end
    end
  endgenerate

  // ----------------------------------------------------------------
  // Step 4: IC error correction column (column DropBits-1)
  // ----------------------------------------------------------------
  wire [DataWidth-1:0] ic_pp;
  generate
    for (i = 0; i < DataWidth; i++) begin : ic_bit_gen
      localparam jj = (DropBits - 1) - i;
      if (jj >= 0 && jj < DataWidth) begin
        assign ic_pp[i] = pp[i][jj];
      end else begin
        assign ic_pp[i] = 1'b0;
      end
    end
  endgenerate

  // edge IC bits: indices 0, 1, D-H-2, D-H-1  (base-0)
  wire [EdgeICWidth-1:0] edge_ic =
    {{EdgeICWidth-1{1'b0}}, ic_pp[0]} +
    {{EdgeICWidth-1{1'b0}}, ic_pp[1]} +
    {{EdgeICWidth-1{1'b0}}, ic_pp[DataWidth - H - 2]} +
    {{EdgeICWidth-1{1'b0}}, ic_pp[DataWidth - H - 1]};

  // middle IC bits: everything else in 0..D-H-1
  wire [MiddleICWidth-1:0] middle_ic;
  generate
    if (MiddleICTermAmt <= 0) begin
      assign middle_ic = 0;
    end else begin
      wire [MiddleICWidth-1:0] mid_parts[0:MiddleICTermAmt-1];
      for (i = 2; i < DataWidth - H - 2; i++) begin : mid_ic_loop
        localparam part_idx = i - 2;
        assign mid_parts[part_idx] = {{MiddleICWidth - 1{1'b0}}, ic_pp[i]};
      end
      // sum the middle parts
      assign middle_ic = mid_parts[0] + mid_parts[1] + mid_parts[2] + mid_parts[3];
    end
  endgenerate

  // ----------------------------------------------------------------
  // Step 5: final accumulation with column weighting
  // ----------------------------------------------------------------
  wire signed [OutputSlice:0] accumulate;
  // sum all columns with appropriate shifts (+1 correction at MSB column)
  wire signed [OutputSlice:0] col_weighted[0:Columns-1];
  generate
    for (c = DropBits; c < OutputWidth; c++) begin : col_weight_gen
      localparam col_idx = c - DropBits;
      localparam shift = c - DropBits + 1;
      if (c == OutputWidth - 1) begin
        // MSB column: add the final "1" correction term
        assign col_weighted[col_idx] =
          ({{{(OutputSlice + 1 - SumWidth){1'b0}}, col_sum[col_idx]} + 1'b1}) << shift;
      end else begin
        assign col_weighted[col_idx] =
          {{{OutputSlice + 1 - SumWidth}{1'b0}}, col_sum[col_idx]} << shift;
      end
    end
  endgenerate

  assign accumulate = col_weighted[0]
    + col_weighted[1]
    + col_weighted[2]
    + col_weighted[3]
    + col_weighted[4]
    + col_weighted[5]
    + col_weighted[6]
    + col_weighted[7]
    + col_weighted[8]
    + col_weighted[9]
    + col_weighted[10]
    + col_weighted[11]
    + col_weighted[12]
    + col_weighted[13]
    + col_weighted[14]
    + col_weighted[15]
    + {{OutputSlice + 1 - EdgeICWidth{1'b0}}, edge_ic}
    + ({{{OutputSlice + 1 - MiddleICWidth{1'b0}}, middle_ic}} << 1);

  assign out = accumulate[OutputSlice:1];

endmodule

`default_nettype wire
