package kr.ac.u1.askcampus

import android.content.Context
import android.os.Bundle
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import kotlinx.coroutines.launch
import kr.ac.u1.askcampus.databinding.ActivityMainBinding

/**
 * 채팅 화면 (SCR-001) MVP.
 * 질문 → 서버 POST /api/v1/ask → 답변·출처 표시. 근거가 없으면 '학과 조교에게 전달됨' 안내 (FR-005, FR-028).
 * 캠퍼스·서버 주소는 기기에만 저장한다 (2.6).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding
    private val adapter = ChatAdapter { q -> send(q) }
    private val prefs by lazy { getSharedPreferences("settings", Context.MODE_PRIVATE) }
    private var busy = false

    private var campus: String
        get() = prefs.getString("campus", "아산")!!
        set(value) { prefs.edit().putString("campus", value).apply(); updateTitle() }

    private var server: String
        get() = prefs.getString("server", BuildConfig.DEFAULT_SERVER)!!
        set(value) { prefs.edit().putString("server", value).apply() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        b.toolbar.inflateMenu(R.menu.main)
        b.toolbar.setOnMenuItemClickListener {
            when (it.itemId) {
                R.id.action_campus -> chooseCampus()
                R.id.action_server -> editServer()
            }
            true
        }
        updateTitle()

        b.messages.layoutManager = LinearLayoutManager(this).apply { stackFromEnd = true }
        b.messages.adapter = adapter
        adapter.add(ChatMessage(fromUser = false, text = getString(R.string.welcome)))

        b.send.setOnClickListener { sendFromInput() }
        b.input.setOnEditorActionListener { _, id, _ ->
            if (id == EditorInfo.IME_ACTION_SEND) { sendFromInput(); true } else false
        }
        debugAutoAsk(intent)
    }

    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        debugAutoAsk(intent)
    }

    /**
     * 디버그 빌드 전용: adb로 한글 질문을 보내 시험하기 위한 통로 (adb input text는 한글을 못 씀).
     * adb shell am start -n kr.ac.u1.askcampus/.MainActivity --es q64 <UTF-8 질문의 Base64>
     */
    private fun debugAutoAsk(intent: android.content.Intent?) {
        if (!BuildConfig.DEBUG) return
        val q64 = intent?.getStringExtra("q64") ?: return
        intent.removeExtra("q64")
        val q = String(android.util.Base64.decode(q64, android.util.Base64.DEFAULT), Charsets.UTF_8)
        b.input.setText(q)
        sendFromInput()
    }

    private fun updateTitle() {
        b.toolbar.title = getString(R.string.app_name)
        b.toolbar.subtitle = if (campus == "영동") getString(R.string.campus_yeongdong) else getString(R.string.campus_asan)
    }

    private fun sendFromInput() {
        val q = b.input.text.toString().trim()
        if (q.isEmpty() || busy) return          // 빈 입력·중복 전송 방지 (FR-001)
        b.input.setText("")
        send(q)
    }

    private fun send(question: String) {
        if (busy) return
        busy = true
        b.send.isEnabled = false
        adapter.add(ChatMessage(fromUser = true, text = question))
        val loadingAt = adapter.add(ChatMessage(fromUser = false, text = getString(R.string.loading), loading = true))
        scrollToEnd()

        lifecycleScope.launch {
            val msg = try {
                val r = AskApi(server).ask(question, campus)
                ChatMessage(fromUser = false, text = r.answer, sources = r.sources, pending = r.pendingRegistered)
            } catch (e: AskApiException) {
                ChatMessage(fromUser = false, text = e.message ?: getString(R.string.error_network))
            } catch (e: Exception) {
                ChatMessage(fromUser = false, text = getString(R.string.error_network), retryQuestion = question)
            }
            adapter.replace(loadingAt, msg)
            busy = false
            b.send.isEnabled = true
            scrollToEnd()
        }
    }

    private fun scrollToEnd() = b.messages.post { b.messages.scrollToPosition(adapter.itemCount - 1) }

    private fun chooseCampus() {
        val names = arrayOf(getString(R.string.campus_yeongdong), getString(R.string.campus_asan))
        val values = arrayOf("영동", "아산")
        AlertDialog.Builder(this)
            .setTitle(R.string.menu_campus)
            .setSingleChoiceItems(names, values.indexOf(campus)) { d, which -> campus = values[which]; d.dismiss() }
            .show()
    }

    private fun editServer() {
        val input = EditText(this).apply { setText(server); hint = getString(R.string.server_hint); setSingleLine() }
        AlertDialog.Builder(this)
            .setTitle(R.string.menu_server)
            .setView(input)
            .setPositiveButton(R.string.ok) { _, _ ->
                val v = input.text.toString().trim()
                if (v.startsWith("http")) server = if (v.endsWith("/")) v else "$v/"
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }
}
