import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview.vision_models import ImageGenerationModel
from google.oauth2 import service_account
import io

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import the config dataclass, not the loader instance
from core.config import VertexAIConfig

class AIService:
    """A service class to interact with Google Cloud Vertex AI."""

    def __init__(self, config: VertexAIConfig):
        self.config = config
        self.initialized = False
        
        credentials = None
        # If a path to a JSON key is provided, use it for authentication.
        if self.config.credentials_json_path and Path(self.config.credentials_json_path).is_file():
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.credentials_json_path
                )
                print(f"Authenticating to Vertex AI using JSON key: {self.config.credentials_json_path}")
            except Exception as e:
                print(f"[ERROR] Failed to load credentials from JSON file: {e}")
                return
        else:
            # Otherwise, fall back to Application Default Credentials (ADC).
            print("Authenticating to Vertex AI using Application Default Credentials (ADC).")

        try:
            vertexai.init(
                project=self.config.project_id,
                location=self.config.location,
                credentials=credentials
            )
            self.chat_model = GenerativeModel(self.config.models.chat)
            self.image_model = ImageGenerationModel.from_pretrained(self.config.models.image)
            self.initialized = True
            print("Vertex AI Service initialized successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Vertex AI: {e}")
            print("Please check your project settings in 'configs/config.yaml' and your authentication method.")
            self.chat_model = None
            self.image_model = None

    async def ask_question(self, prompt: str) -> str:
        """Generates a text response from a prompt using the chat model."""
        if not self.initialized or not self.chat_model:
            return "The chat model is not available due to an initialization error."

        try:
            response = await self.chat_model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"[ERROR] Vertex AI (Chat): {e}")
            return f"An error occurred while processing your request: {e}"

    async def generate_image(self, prompt: str, number_of_images: int = 1) -> list[io.BytesIO] | str:
        """Generates images from a prompt and returns them as a list of BytesIO objects."""
        if not self.initialized or not self.image_model:
            return "The image model is not available due to an initialization error."

        try:
            response = self.image_model.generate_images(
                prompt=prompt,
                number_of_images=number_of_images,
            )
            image_streams = [io.BytesIO(img._image_bytes) for img in response.images]
            return image_streams
        except Exception as e:
            print(f"[ERROR] Vertex AI (Image): {e}")
            return f"An error occurred while generating the image: {e}"

# Note: The singleton instance is removed. Instantiation is now handled by the DI container.