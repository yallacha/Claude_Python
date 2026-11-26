# build_workbook.py 입력 JSON 형식

UTF-8로 저장한다. 산출물 폴더에 남겨 두면 나중에 케이스를 고치고 엑셀을 다시 만들 수 있다.

```json
{
  "title": "BCM 도어 잠금 SW 시스템 테스트 명세",
  "basis_document": "BCM_SRS_v1.2.docx",
  "requirements": [
    {
      "id": "REQ-001",
      "title": "차속 연동 자동 잠금",
      "text": "차속이 15 km/h 이상이 되면 1 s 이내에 모든 도어를 잠근다.",
      "category": "functional",
      "asil": "B",
      "testable": true,
      "has_inputs": true,
      "has_ranges": true
    }
  ],
  "test_cases": [
    {
      "id": "TC-F-001",
      "basis_ids": ["REQ-001"],
      "category": "functional",
      "source": "basis",
      "proposed": false,
      "purpose": "자동 잠금 임계값(15 km/h) 경계에서 잠금 여부 확인",
      "preconditions": "IGN ON, 모든 도어 닫힘·잠금 해제, 기어 D",
      "inputs": "VehSpd = 15.0 km/h (경계값)",
      "procedure": "1. VehSpd를 0.0 km/h에서 15.0 km/h로 변경\n2. 변경 시점부터 DoorLockCmd 관측",
      "expected": "변경 후 1 s 이내 DoorLockCmd = LOCK",
      "pass_criteria": "1000 ms 이내 LOCK 전송",
      "environment": "HIL (CANoe)",
      "techniques": ["경계값 분석", "요구사항 기반"],
      "priority": "High",
      "remarks": ""
    }
  ],
  "design": [
    {
      "id": "BV-REQ-001-02",
      "basis_id": "REQ-001",
      "technique": "경계값 분석",
      "item": "VehSpd 잠금 임계값",
      "values": "15.0 km/h (경계, 분해능 0.1)",
      "covered_by": ["TC-F-001"],
      "applicable": true,
      "note": ""
    },
    {
      "id": "PW-REQ-001-NA",
      "basis_id": "REQ-001",
      "technique": "페어와이즈(PICT)",
      "item": "적용 검토",
      "values": "",
      "covered_by": [],
      "applicable": false,
      "note": "독립 파라미터 1개(VehSpd)라 적용 대상 아님"
    }
  ],
  "pict_models": [
    {"basis_id": "REQ-012", "model_file": "pict_model_REQ-012.txt", "result_file": "pict_result_REQ-012.tsv", "order": 2, "rows": 16}
  ],
  "open_issues": [
    {"id": "Q-01", "basis_id": "REQ-007", "question": "차속 신호 무효(0x3FF) 수신 시 동작이 정의되지 않음", "impact": "무효 클래스 케이스 보류"}
  ]
}
```

## 필드 규칙

**최상위**
- `basis_document`: 사용자가 준 테스트 베이시스 문서 이름(파일명, 문서 번호, 버전). 비어 있으면 스크립트가 실패한다. 베이시스 없이 케이스를 만들지 않기 위한 장치다.
- `sample`: 사용자가 예시를 명시적으로 요청해 `SAMPLE-` 요구사항을 쓴 경우에만 `true`. 커버리지 요약 시트 맨 위에 예시 산출물이라는 경고가 붙는다.

**requirements**
- `category`: `functional` 또는 `non-functional`
- `testable`: `false`이면 같은 `basis_id`의 `open_issues`가 있어야 한다. 커버리지 분모에서 빠지고 별도로 보고된다.
- `has_inputs`: 입력·상태·이벤트가 있으면 `true` → 이 요구사항에 `동치 분할` design 항목이 있어야 한다.
- `has_ranges`: 순서가 있는 범위가 있으면 `true` → `경계값 분석` design 항목이 있어야 한다.

**test_cases**
- `id`: 고유. 기능은 `TC-F-###`, 비기능은 `TC-NF-###`을 권장.
- `category`: 케이스가 들어갈 시트를 정한다.
- `source`: `basis`(베이시스에서 도출), `user`(사용자가 준 케이스), `claude`(Claude가 추가 제안).
- `proposed`: `source`가 `claude`이면 `true`. 스크립트가 테스트 목적 앞에 `[제안]`을 붙인다(이미 있으면 그대로 둔다). [제안] 케이스는 베이시스 커버리지 계산에 들어가지 않는다.
- `techniques`: `techniques.md` 6절의 이름만 쓴다.
- 비어 있으면 안 되는 항목: `id`, `basis_ids`, `purpose`, `inputs`, `procedure`, `expected`, `techniques`. 양식을 쓸 때도 이 항목은 채운다(양식에 열이 없으면 엑셀에 안 나올 뿐이다).

**design**
- `applicable: false` 항목은 "검토했지만 적용 대상 아님"의 기록이다. `note`에 이유를 쓴다.
- 적용 항목은 `covered_by`에 실제 존재하고, 같은 `basis_id`를 추적하는 케이스가 1개 이상 있어야 한다.

## 사용자 양식 적용 (`--template`)

사용자가 엑셀 양식을 주면 JSON에 `template`을 추가하고 `--template <양식.xlsx>`로 실행한다.

```json
"template": {
  "sheet": "TestCase",
  "header_row": 5,
  "columns": {
    "No.": "id",
    "Requirement ID": "basis_ids",
    "Test Objective": "purpose",
    "Precondition": "preconditions",
    "Test Input": "inputs",
    "Test Step": "procedure",
    "Expected Result": "expected",
    "Test Method": "techniques",
    "Result": "result"
  }
}
```

- `sheet`: 양식 시트 이름(없으면 첫 시트). 이 시트를 복사해 `기능 테스트`, `비기능 테스트` 시트를 만들고, 원래 시트는 지운다. 양식의 다른 시트(표지, 개정 이력 등)는 그대로 둔다.
- `header_row`: 머리글이 있는 행 번호. 케이스는 그 아래 행부터 쓴다.
- `columns`: 양식의 머리글 글자 → 필드 이름. 양식에 있는데 매핑할 필드가 없는 열은 비워 둔다.
- 쓸 수 있는 필드: `id`, `basis_ids`, `division`(일반/[제안]), `purpose`, `preconditions`, `inputs`, `procedure`, `expected`, `pass_criteria`, `techniques`, `environment`, `asil`, `priority`, `result`(빈칸), `verdict`(빈칸), `remarks`
- 양식에 테스트 베이시스 ID 열이 없어도 추적성은 `추적성 매트릭스` 시트에 남는다. 이 사실을 사용자에게 알린다.
