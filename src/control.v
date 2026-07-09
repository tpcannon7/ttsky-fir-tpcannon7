module control (
    input wire clk,
    input wire rst_n,

    input  wire [7:0] spi_rx_byte,
    output wire [7:0] spi_tx_byte,

    input  wire [15:0] dout_fir,
    output wire [15:0] din_fir,
);

endmodule
