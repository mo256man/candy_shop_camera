import os
import numpy as np
import insightface

# モデルは server/models/buffalo_l/ に配置
# このファイル自体が server/ にあるため root = server/ = __file__ の親ディレクトリ
_model_root = os.path.dirname(os.path.abspath(__file__))
_app = insightface.app.FaceAnalysis(name="buffalo_l", root=_model_root)
_app.prepare(ctx_id=-1)  # CPU: -1 / GPU: 0


def analyze_face(face_img):
    """
    顔画像から年齢・性別を推論する。

    Parameters
    ----------
    face_img : numpy.ndarray
        BGR 形式の顔画像（OpenCV で読み込んだ画像）

    Returns
    -------
    ret    : bool – 年齢・性別が取得できた場合 True
    age    : int  – 推定年齢（取得失敗時は None）
    gender : str  – "M" / "F" / None
    """
    try:
        faces = _app.get(face_img)

        if not faces:
            return False, None, None

        face = faces[0]

        age = int(face.age) if hasattr(face, "age") and face.age is not None else None
        if hasattr(face, "gender") and face.gender is not None:
            gender = "M" if face.gender == 1 else "F"
        else:
            gender = None

        if age is None or gender is None:
            return False, None, None

        return True, age, gender

    except Exception as e:
        # print(f"[InsightFace Error] {e}")
        return False, None, None
