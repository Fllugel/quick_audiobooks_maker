from src.ui import AudiobookUI

def main():
    ui = AudiobookUI()
    interface = ui.create_ui()
    interface.launch(share=False)

if __name__ == "__main__":
    main() 