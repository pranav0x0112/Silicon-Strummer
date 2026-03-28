/*
 * Silicon Strummer — VGA Fretboard Guitar
 * SPDX-License-Identifier: Apache-2.0
 *
 * ui_in[0] : move right  (fret +)
 * ui_in[1] : move left   (fret -)
 * ui_in[2] : move up     (string -)
 * ui_in[3] : move down   (string +)
 * ui_in[4] : enable sound
 *
 * TinyVGA PMOD:  uo_out  = {hsync, B[0], G[0], R[0], vsync, B[1], G[1], R[1]}
 * Audio:         uio_out = {sound, 7'b0}   uio_oe = 8'hff
 */

`default_nettype none

module tt_um_silicon_strummer (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    wire hsync, vsync, video_active;
    wire [9:0] x, y;

    hvsync_generator hvsync_gen (
        .clk        (clk),
        .reset      (~rst_n),
        .hsync      (hsync),
        .vsync      (vsync),
        .display_on (video_active),
        .hpos       (x),
        .vpos       (y)
    );

    wire [1:0] R, G, B;
    assign uo_out  = {hsync, B[0], G[0], R[0], vsync, B[1], G[1], R[1]};
    assign uio_oe  = 8'hff;
    assign uio_out = {audio_out, 7'b0};

    reg [4:0] btn_s0, btn_s1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            btn_s0 <= 0;
            btn_s1 <= 0;
        end else begin
            btn_s0 <= ui_in[4:0];
            btn_s1 <= btn_s0;
        end
    end

    reg [2:0] fret_pos;
    reg [2:0] str_pos;
    reg vsync_prev;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fret_pos   <= 0;
            str_pos    <= 0;
            vsync_prev <= 0;
        end else begin
            vsync_prev <= vsync;
            if (vsync & ~vsync_prev) begin
                if (btn_s1[0] && fret_pos < 3'd7) fret_pos <= fret_pos + 1;
                if (btn_s1[1] && fret_pos > 3'd0) fret_pos <= fret_pos - 1;
                if (btn_s1[2] && str_pos  > 3'd0) str_pos  <= str_pos  - 1;
                if (btn_s1[3] && str_pos  < 3'd5) str_pos  <= str_pos  + 1;
            end
        end
    end

    wire [9:0] cell_col_w = x / 10'd80;
    wire [9:0] cell_row_w = y / 10'd80;
    wire [9:0] cell_x_w   = x % 10'd80;
    wire [9:0] cell_y_w   = y % 10'd80;

    wire [2:0] cell_col   = cell_col_w[2:0];
    wire [2:0] cell_row   = cell_row_w[2:0];
    wire [6:0] cell_x     = cell_x_w[6:0];
    wire [6:0] cell_y     = cell_y_w[6:0];

    wire is_cursor   = (cell_col == fret_pos) && (cell_row == str_pos);
    wire grid_line   = (cell_x >= 7'd78) || (cell_y >= 7'd78);
    wire string_line = (cell_y >= 7'd38) && (cell_y <= 7'd41);

    reg [1:0] r_reg, g_reg, b_reg;
    always @(*) begin
        r_reg = 2'b00; g_reg = 2'b00; b_reg = 2'b00;
        if (video_active) begin
            if (is_cursor) begin
                if (grid_line) begin
                    r_reg = 2'b11; g_reg = 2'b11; b_reg = 2'b11;
                end else begin
                    r_reg = 2'b11; g_reg = 2'b11; b_reg = 2'b00;
                end
            end else begin
                if (grid_line)        begin r_reg = 2'b00; g_reg = 2'b00; b_reg = 2'b01; end
                else if (string_line) begin r_reg = 2'b00; g_reg = 2'b01; b_reg = 2'b00; end
            end
        end
    end

    assign R = r_reg;
    assign G = g_reg;
    assign B = b_reg;

    wire [5:0]  note        = {str_pos, fret_pos};
    wire [16:0] note_scaled = note * 17'd2510;
    wire [16:0] divider     = (note_scaled >= 17'd125000) ? 17'd6250
                                                           : 17'd125000 - note_scaled;
    reg [16:0] audio_cnt;
    reg        audio_out;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            audio_cnt <= 0;
            audio_out <= 0;
        end else if (btn_s1[4]) begin
            if (audio_cnt == 0) begin
                audio_cnt <= divider;
                audio_out <= ~audio_out;
            end else begin
                audio_cnt <= audio_cnt - 1;
            end
        end else begin
            audio_out <= 0;
            audio_cnt <= 0;
        end
    end

    wire _unused = &{ena, uio_in, 1'b0};

endmodule