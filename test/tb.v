`default_nettype none `timescale 1ns / 1ps

module tb ();

  // Dump the signals to a FST file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;

  reg spi_clock, spi_cs_n, spi_mosi, fir_mode;
  wire spi_miso;
  reg [6:0] ui_in_extra = {7{1'b0}};

  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  assign ui_in[0] = fir_mode;
  assign ui_in[7:1] = ui_in_extra;

  assign spi_miso = uio_out[2];
  assign uio_in[0] = spi_cs_n;
  assign uio_in[1] = spi_mosi;
  assign uio_in[2] = 1'b0;
  assign uio_in[3] = spi_clock;
  assign uio_in[7:4] = {4{1'b0}};

`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  tt_um_tpcannon7_fir tt_um_tpcannon7_fir (

      // Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif

      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

endmodule
