"""Unit tests for Antigravity native image generation."""
import unittest

from antigravity_auth.image import (
    assert_safe_aspect_ratio,
    build_image_generate_request,
    parse_image_response_payload,
    IMAGE_ASPECT_RATIOS,
    DEFAULT_IMAGE_MODEL,
)


class TestAntigravityImage(unittest.TestCase):
    def test_aspect_ratios(self):
        for ratio in IMAGE_ASPECT_RATIOS:
            self.assertEqual(assert_safe_aspect_ratio(ratio), ratio)

        with self.assertRaises(ValueError):
            assert_safe_aspect_ratio("invalid:ratio")

    def test_build_image_request(self):
        req = build_image_generate_request(
            prompt="A cute cat on Mars",
            project_id="test-proj-123",
            aspect_ratio="16:9",
            model=DEFAULT_IMAGE_MODEL,
        )
        self.assertEqual(req["project"], "test-proj-123")
        self.assertEqual(req["model"], DEFAULT_IMAGE_MODEL)
        self.assertEqual(req["requestType"], "image_gen")
        self.assertEqual(req["userAgent"], "antigravity")

        contents = req["request"]["contents"]
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0]["role"], "user")
        self.assertEqual(contents[0]["parts"][0]["text"], "A cute cat on Mars")

        image_config = req["request"]["generationConfig"]["imageConfig"]
        self.assertEqual(image_config["aspectRatio"], "16:9")

    def test_parse_image_payload_json(self):
        raw_json = """
        {
          "candidates": [
            {
              "content": {
                "parts": [
                  {"text": "Generating image..."},
                  {
                    "inlineData": {
                      "mimeType": "image/png",
                      "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                    }
                  }
                ]
              }
            }
          ]
        }
        """
        images, text = parse_image_response_payload(raw_json)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["mimeType"], "image/png")
        self.assertTrue(images[0]["data"].startswith("iVBORw0KGgo"))
        self.assertEqual(text, ["Generating image..."])

    def test_parse_image_payload_sse(self):
        sse_text = (
            'data: {"candidates":[{"content":{"parts":[{"text":"Rendering..."}]}}]}\n\n'
            'data: {"candidates":[{"content":{"parts":[{"inlineData":{"mimeType":"image/jpeg","data":"/9j/4AAQSkZJRg=="}}]}}]}\n\n'
            'data: [DONE]\n'
        )
        images, text = parse_image_response_payload(sse_text)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["mimeType"], "image/jpeg")
        self.assertEqual(images[0]["data"], "/9j/4AAQSkZJRg==")
        self.assertEqual(text, ["Rendering..."])


if __name__ == "__main__":
    unittest.main()
