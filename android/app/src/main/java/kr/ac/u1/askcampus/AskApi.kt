package kr.ac.u1.askcampus

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** 출처 한 건 (API 명세 1-2 sources[]) */
data class Source(
    val title: String,
    val kind: String,
    val url: String?,
    val menuPath: String?,
    val collectedAt: String?,
)

/** POST /api/v1/ask 응답 */
data class AskResult(
    val answerType: String,          // 문서 / FAQ / 되묻기 / 근거없음
    val answer: String,
    val sources: List<Source>,
    val pendingRegistered: Boolean,
    val elapsedMs: Int,
)

class AskApiException(message: String) : Exception(message)

class AskApi(private val baseUrl: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .callTimeout(30, TimeUnit.SECONDS)   // sLLM 답변 생성 시간 포함
        .build()

    suspend fun ask(question: String, campus: String?): AskResult = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("question", question)
            .put("campus", campus ?: JSONObject.NULL)
            .toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url(baseUrl.trimEnd('/') + "/api/v1/ask").post(body).build()
        client.newCall(request).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            val json = runCatching { JSONObject(text) }.getOrNull()
            if (!resp.isSuccessful || json == null) {
                val msg = json?.optJSONObject("error")?.optString("message")
                throw AskApiException(msg?.takeIf { it.isNotBlank() } ?: "서버 오류 (${resp.code})")
            }
            parse(json)
        }
    }

    private fun parse(json: JSONObject): AskResult {
        val arr = json.optJSONArray("sources")
        val sources = (0 until (arr?.length() ?: 0)).map { i ->
            val s = arr!!.getJSONObject(i)
            Source(
                title = s.optString("title"),
                kind = s.optString("kind"),
                url = s.optString("source_url").takeIf { it.isNotBlank() && it != "null" },
                menuPath = s.optString("menu_path").takeIf { it.isNotBlank() && it != "null" },
                collectedAt = s.optString("collected_at").takeIf { it.isNotBlank() && it != "null" },
            )
        }
        return AskResult(
            answerType = json.optString("answer_type"),
            answer = json.optString("answer"),
            sources = sources,
            pendingRegistered = json.optBoolean("pending_registered"),
            elapsedMs = json.optInt("elapsed_ms"),
        )
    }
}
