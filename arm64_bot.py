from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import struct

# ============================
# CONFIG
# ============================
TOKEN = "8134204437:AAEaoyvLgGxiREmIYyAGaBxqTzDNux5Pez8"  # your bot token


# ============================
# CORE LOGIC (ported from your bash script)
# ============================

def word_to_hex_le(w: int) -> str:
    """Print 32-bit word as bytes (little-endian)"""
    return " ".join(f"{(w >> (8 * i)) & 0xFF:02X}" for i in range(4))


def gen_mov_immediate(v: int, is32: bool, use_fmov: bool = False) -> str:
    """
    Generate MOVZ / MOVK sequence + optional FMOV + RET
    Returns formatted string like your script.
    """
    # Ensure 64-bit unsigned
    v &= 0xFFFFFFFFFFFFFFFF

    # Constants (same as your bash script)
    movzW = 0x52800000
    movkW = 0x72800000
    movzX = 0xD2800000
    movkX = 0xF2800000
    ret = 0xD65F03C0
    fmov = 0x9E670400

    # Split into 16-bit chunks
    p1 = v & 0xFFFF
    p2 = (v >> 16) & 0xFFFF
    p3 = (v >> 32) & 0xFFFF
    p4 = (v >> 48) & 0xFFFF

    asm_lines = []
    hex_all = []

    if is32:
        # MOVZ W0
        ins = movzW | (p1 << 5)
        asm_lines.append(f"~A8 MOVZ W0, #0x{p1:X}")
        hex_all.append(word_to_hex_le(ins))

        # MOVK W0, LSL #16
        if p2 != 0:
            ins = movkW | (1 << 21) | (p2 << 5)
            asm_lines.append(f"~A8 MOVK W0, #0x{p2:X}, LSL #16")
            hex_all.append(word_to_hex_le(ins))
    else:
        # MOVZ X0
        ins = movzX | (p1 << 5)
        asm_lines.append(f"~A8 MOVZ X0, #0x{p1:X}")
        hex_all.append(word_to_hex_le(ins))

        # MOVK X0, LSL #16
        if p2 != 0:
            ins = movkX | (1 << 21) | (p2 << 5)
            asm_lines.append(f"~A8 MOVK X0, #0x{p2:X}, LSL #16")
            hex_all.append(word_to_hex_le(ins))

        # MOVK X0, LSL #32
        if p3 != 0:
            ins = movkX | (2 << 21) | (p3 << 5)
            asm_lines.append(f"~A8 MOVK X0, #0x{p3:X}, LSL #32")
            hex_all.append(word_to_hex_le(ins))

        # MOVK X0, LSL #48
        if p4 != 0:
            ins = movkX | (3 << 21) | (p4 << 5)
            asm_lines.append(f"~A8 MOVK X0, #0x{p4:X}, LSL #48")
            hex_all.append(word_to_hex_le(ins))

        # Optional FMOV D0, X0 (like USE_FMOV=1)
        if use_fmov:
            asm_lines.append("~A8 FMOV D0, X0")
            hex_all.append(word_to_hex_le(fmov))

    # RET
    asm_lines.append("~A8 RET")
    hex_all.append(word_to_hex_le(ret))

    asm_text = "\n".join(asm_lines)
    hex_text = " ".join(hex_all)

    out = (
        "🔹 ASSEMBLY (VIEW):\n"
        f"{asm_text}\n\n"
        "🔹 COMBINED HEX:\n"
        f"{hex_text}\n"
    )
    return out


def float_to_u64(f: float) -> int:
    """Same as your float_to_u64() in bash (double)"""
    return struct.unpack("<Q", struct.pack("<d", float(f)))[0]


# ============================
# TELEGRAM BOT HANDLERS
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 ARM64 HEX + ASM Generator Bot\n\n"
        "Commands:\n"
        "  /bool <0|1>\n"
        "  /int <value>\n"
        "  /float <value>\n"
        "  /long <value>\n\n"
        "Example:\n"
        "  /bool 1\n"
        "  /int 123\n"
        "  /float 100.0\n"
        "  /long 1234567890123\n"
    )
    await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def bool_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /bool 0 or /bool 1")
        return

    try:
        val = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid bool. Use 0 or 1.")
        return

    val = 1 if val != 0 else 0
    result = gen_mov_immediate(val, is32=True)
    await update.message.reply_text(result)


async def int_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /int <integer>")
        return

    try:
        val = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid integer.")
        return

    result = gen_mov_immediate(val, is32=True)
    await update.message.reply_text(result)


async def float_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /float <value>")
        return

    try:
        fval = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid float.")
        return

    bits = float_to_u64(fval)
    result = gen_mov_immediate(bits, is32=False)
    await update.message.reply_text(result)


async def long_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /long <64-bit integer>")
        return

    try:
        val = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid 64-bit integer.")
        return

    result = gen_mov_immediate(val, is32=False)
    await update.message.reply_text(result)


# ============================
# MAIN
# ============================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(CommandHandler("bool", bool_cmd))
    app.add_handler(CommandHandler("int", int_cmd))
    app.add_handler(CommandHandler("float", float_cmd))
    app.add_handler(CommandHandler("long", long_cmd))

    print("ARM64 ASM bot running…")
    app.run_polling()


if __name__ == "__main__":
    main()