import unittest

import numpy as np
from PIL import Image

from polaroid import _circle_crop


class TestPolaroidAlpha(unittest.TestCase):
    def test_circle_edge_does_not_get_dark_halo(self):
        # Imagem sólida facilita detectar escurecimento artificial no contorno.
        src = Image.new("RGB", (1200, 1200), (240, 50, 50))
        out = _circle_crop(src)
        arr = np.array(out, dtype=np.uint8)

        alpha = arr[:, :, 3]
        edge = (alpha > 15) & (alpha < 240)

        self.assertTrue(edge.any(), "Máscara de borda esperada não encontrada.")

        # Corrige a cor para "straight alpha" (desfaz premultiplicação visual).
        edge_alpha = alpha[edge].astype(np.float32)
        edge_red = arr[:, :, 0][edge].astype(np.float32)
        edge_red_straight = np.clip((edge_red * 255.0) / np.maximum(edge_alpha, 1.0), 0, 255)
        edge_red_mean = edge_red_straight.mean()

        # Sem vignette, a cor recuperada na borda fica próxima do vermelho original (240).
        self.assertGreater(
            edge_red_mean,
            220,
            f"Borda escurecida detectada (média do canal R: {edge_red_mean:.2f}).",
        )


if __name__ == "__main__":
    unittest.main()
