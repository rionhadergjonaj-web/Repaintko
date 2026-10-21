"""Repaintko 13.1.0: Python image editor with a custom Qt interface, without Tk."""
import sys
try:
    from document import Document, checked_size, load_image, DEFAULT_SIZE, MAX_PIXELS
    from qt_app import Repainko, main
except Exception:
    if '--smoke-test' in sys.argv:
        import traceback
        from pathlib import Path
        Path(sys.argv[sys.argv.index('--smoke-test')+1]).write_text(traceback.format_exc(), encoding='utf-8')
        sys.exit(1)
    raise

if __name__ == '__main__':
    main()
