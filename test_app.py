import gradio as gr

def echo(message, history):
    return history + [[message, f"Echo: {message}"]]

demo = gr.ChatInterface(echo)

if __name__ == "__main__":
    demo.launch()