`default_nettype none

module fir_filter #(
    parameter SAMPLE_WIDTH = 8,
    parameter COEFF_WIDTH = 8,
    parameter TAPS = 8
) (
    input wire clk,
    input wire ena,
    input wire rst_n,
    input wire signed [SAMPLE_WIDTH-1:0] din,

    output wire signed [SAMPLE_WIDTH-1:0] dout
);

localparam OUT_WIDTH = SAMPLE_WIDTH + COEFF_WIDTH + TAPS;
localparam signed [COEFF_WIDTH-1:0] COEFF_VAL = 8'h10;


reg signed [OUT_WIDTH-1:0] output_r;
reg signed [SAMPLE_WIDTH-1:0] samples [0:TAPS-2];
wire signed [(SAMPLE_WIDTH + COEFF_WIDTH)-1:0] taps_out [0:TAPS-1];
reg signed [OUT_WIDTH-1:0] out_full;

assign taps_out[0] = din * COEFF_VAL;

always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
        samples[0] <= 0;
    end else begin
        samples[0] <= din;
    end
end

genvar i;
generate
    for (i = 1; i < TAPS; i = i + 1) begin
        assign taps_out[i] = samples[i-1] * COEFF_VAL;
    end

    for (i = 1; i < TAPS - 1; i = i + 1) begin
        always @(posedge clk or negedge rst_n) begin
            if (~rst_n) begin
                samples[i] <= 0;
            end else begin
                samples[i] <= samples[i-1];
            end
        end
    end
endgenerate

always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
        output_r <= 0;
    end else begin
        if (ena) begin
            output_r <= out_full;
        end
    end
end

integer j;
always @(*) begin
    out_full = 0;
    for (j = 0; j < TAPS; j = j + 1) begin
        // gross
        out_full = out_full + {{(OUT_WIDTH-SAMPLE_WIDTH-COEFF_WIDTH){taps_out[j][SAMPLE_WIDTH+COEFF_WIDTH-1]}}, taps_out[j]};
    end
end

// change to correct bit slice
assign dout = output_r[13 -: 6];

endmodule