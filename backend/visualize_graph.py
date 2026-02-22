import os
import sys

# Add the project root to the python path to allow importing modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.chatbot import RAGChatbot

def visualize_chatbot_workflow():
    """
    Visualize the chatbot workflow using LangGraph's built-in visualization capabilities.
    """
    print("Initializing chatbot and workflow...")
    try:
        # Initialize the chatbot which builds the workflow
        chatbot = RAGChatbot()
        
        print("Generating workflow visualization...")
        
        # Get the graph object from the compiled workflow
        # The workflow attribute in RAGChatbot is already compiled
        graph = chatbot.workflow.get_graph()
        
        # Generate the PNG image using Mermaid
        # Note: This requires the 'langgraph' library to be installed
        try:
            png_data = graph.draw_mermaid_png()
            
            output_file = "chatbot_workflow.png"
            with open(output_file, "wb") as f:
                f.write(png_data)
                
            print(f"✅ Workflow chart successfully saved to: {os.path.abspath(output_file)}")
            
        except Exception as e:
            print(f"❌ Could not generate PNG image directly: {e}")
            print("This might be due to missing dependencies for image generation.")
            print("Attempting to output Mermaid definition instead...")
            
            mermaid_def = graph.draw_mermaid()
            print("\n" + "="*50)
            print("Mermaid Graph Definition:")
            print("="*50)
            print(mermaid_def)
            print("="*50 + "\n")
            print("You can copy the above text and paste it into https://mermaid.live/ to view the chart.")
            
            # Save mermaid definition to file
            mermaid_file = "chatbot_workflow.mermaid"
            with open(mermaid_file, "w", encoding="utf-8") as f:
                f.write(mermaid_def)
            print(f"Saved mermaid definition to {mermaid_file}")

    except Exception as e:
        print(f"❌ An error occurred during initialization: {e}")

if __name__ == "__main__":
    visualize_chatbot_workflow()
