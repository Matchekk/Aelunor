ERROR_CODE_NARRATOR_RESPONSE = "NARRATOR_RESPONSE_ERROR"
ERROR_CODE_JSON_REPAIR = "JSON_REPAIR_ERROR"
ERROR_CODE_SCHEMA_VALIDATION = "SCHEMA_VALIDATION_ERROR"
ERROR_CODE_PATCH_SANITIZE = "PATCH_SANITIZE_ERROR"
ERROR_CODE_PATCH_APPLY = "PATCH_APPLY_ERROR"
ERROR_CODE_EXTRACTOR = "EXTRACTOR_ERROR"
ERROR_CODE_NORMALIZE = "NORMALIZE_ERROR"
ERROR_CODE_PERSISTENCE = "PERSISTENCE_ERROR"
ERROR_CODE_SSE_BROADCAST = "SSE_BROADCAST_ERROR"
ERROR_CODE_TURN_INTERNAL = "TURN_INTERNAL_ERROR"

TURN_ERROR_USER_MESSAGES = {
    ERROR_CODE_NARRATOR_RESPONSE: "Die KI-Antwort konnte gerade nicht verarbeitet werden.",
    ERROR_CODE_JSON_REPAIR: "Die KI-Antwort war unvollständig oder ungültig formatiert.",
    ERROR_CODE_SCHEMA_VALIDATION: "Die KI-Antwort passte nicht zum erwarteten Datenformat.",
    ERROR_CODE_PATCH_SANITIZE: "Die KI-Änderungen konnten nicht sicher bereinigt werden.",
    ERROR_CODE_PATCH_APPLY: "Die KI-Änderungen konnten nicht auf den Spielzustand angewendet werden.",
    ERROR_CODE_EXTRACTOR: "Die Kanon-Extraktion konnte nicht abgeschlossen werden.",
    ERROR_CODE_NORMALIZE: "Der Kampagnenzustand konnte nicht stabilisiert werden.",
    ERROR_CODE_PERSISTENCE: "Die Kampagne konnte nicht gespeichert werden.",
    ERROR_CODE_SSE_BROADCAST: "Das Live-Update konnte nicht verteilt werden.",
    ERROR_CODE_TURN_INTERNAL: "Beim Verarbeiten des Zugs ist ein interner Fehler aufgetreten.",
}
