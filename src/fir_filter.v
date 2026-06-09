`default_nettype none

module fir_filter #(
    parameter SampleWidth = 8,
    parameter CoeffWidth = 8,
    parameter Taps = 8
) (
    input wire clk,
    input wire ena,
    input wire rst_n,
    input wire signed [SampleWidth-1:0] din,
    input wire [$clog2(Taps)-1:0] tap_sel,
    input wire load,

    output wire signed [SampleWidth-1:0] dout,
    output wire out_valid
);

  localparam OutWidth = SampleWidth + CoeffWidth + $clog2(Taps);

  localparam [1:0] Idle = 2'b00, Load = 2'b01, Compute = 2'b10;
  reg [1:0] curr_st, next_st;

  // state machine
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      curr_st <= Idle;
    end else begin
      curr_st <= next_st;
    end
  end

  always @(*) begin
    next_st = curr_st;
    case (curr_st)
      Idle: begin
        if (load) begin
          next_st = Load;
        end else begin
          next_st = Idle;
        end
      end
      Load: begin
        if (load) begin
          next_st = Load;
        end else begin
          next_st = Compute;
        end
      end
      Compute: begin
        if (load) begin
          next_st = Load;
        end else begin
          next_st = Compute;
        end
      end
      default: begin
        next_st = Idle;
      end
    endcase
  end

  reg signed [OutWidth-1:0] output_r;
  reg signed [SampleWidth-1:0] samples[0:Taps-2];
  wire signed [(SampleWidth + CoeffWidth)-1:0] taps_out[0:Taps-1];
  reg signed [OutWidth-1:0] out_full;
  reg signed [CoeffWidth-1:0] coeff[0:Taps-1];

  // load incoming sample
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      samples[0] <= {SampleWidth{1'b0}};
    end else if (curr_st == Compute) begin
      samples[0] <= din;
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      for (j = 0; j < Taps; j = j + 1) begin
        coeff[j] <= {CoeffWidth{1'b0}};
      end
    end else if (curr_st == Load) begin
      coeff[tap_sel] <= din;
    end
  end

  assign taps_out[0] = din * coeff[0];

  genvar i;
  generate
    // tap outputs
    for (i = 1; i < Taps; i = i + 1) begin
      assign taps_out[i] = samples[i-1] * coeff[i];
    end
    // big shift reg
    for (i = 1; i < Taps - 1; i = i + 1) begin
      always @(posedge clk or negedge rst_n) begin
        if (~rst_n) begin
          samples[i] <= 0;
        end else if (curr_st == Compute) begin
          samples[i] <= samples[i-1];
        end
      end
    end
  endgenerate

  // output reg
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      output_r <= 0;
    end else begin
      if (ena) begin
        output_r <= out_full;
      end
    end
  end

  // adder chain for output
  integer j;
  always @(*) begin
    out_full = 0;
    for (j = 0; j < Taps; j = j + 1) begin
      // gross
      out_full = out_full + {{(OutWidth-SampleWidth-CoeffWidth){taps_out[j][SampleWidth+CoeffWidth-1]}}, taps_out[j]};
    end
  end

  // TODO: change to correct bit slice
  assign dout = output_r[14:7];

endmodule
