from deepface import DeepFace

def analyze_face(face_img):
  try:
    results = DeepFace.analyze(
      face_img,
      actions=["age", "gender"],
      enforce_detection = True,       # 顔が検出されない場合は例外を発生させる
      align = True,                   # 顔のアライメントを有効にする
      silent = True
    )
        
    if not isinstance(results, list) or len(results) == 0:
      return False, None, None, None, None
        
    result = results[0]
    age = result["age"]
    if result["dominant_gender"] == "Man":
      gender = "M"
    elif result["dominant_gender"] == "Woman":
      gender = "F"
    else:
      gender = "U"  # Unknown
    
    male_prob = result["gender"]["Man"]
    female_prob = result["gender"]["Woman"]

    return True, age, gender, male_prob, female_prob

  except Exception as e:
    # print(f"[DeepFace Error] {e}")
    return False, None, None, None, None
