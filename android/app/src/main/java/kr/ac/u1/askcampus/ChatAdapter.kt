package kr.ac.u1.askcampus

import android.content.Intent
import android.net.Uri
import android.text.SpannableStringBuilder
import android.text.style.ForegroundColorSpan
import android.text.style.StyleSpan
import android.graphics.Typeface
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView

/** 채팅 말풍선 한 개 */
data class ChatMessage(
    val fromUser: Boolean,
    val text: String,
    val sources: List<Source> = emptyList(),
    val pending: Boolean = false,
    val loading: Boolean = false,
    val retryQuestion: String? = null,   // 연결 실패 말풍선을 누르면 다시 보낼 질문
)

class ChatAdapter(private val onRetry: (String) -> Unit) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val items = mutableListOf<ChatMessage>()

    fun add(m: ChatMessage): Int {
        items.add(m)
        notifyItemInserted(items.lastIndex)
        return items.lastIndex
    }

    fun replace(index: Int, m: ChatMessage) {
        items[index] = m
        notifyItemChanged(index)
    }

    override fun getItemCount() = items.size
    override fun getItemViewType(position: Int) = if (items[position].fromUser) 0 else 1

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        val layout = if (viewType == 0) R.layout.item_user else R.layout.item_bot
        return object : RecyclerView.ViewHolder(inflater.inflate(layout, parent, false)) {}
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val m = items[position]
        val v = holder.itemView
        val text = v.findViewById<TextView>(R.id.text)
        text.text = m.text
        if (m.fromUser) return

        val ctx = v.context
        text.setTextColor(ContextCompat.getColor(ctx, if (m.loading) R.color.muted else R.color.ink))

        val note = v.findViewById<TextView>(R.id.note)
        note.visibility = if (m.pending) View.VISIBLE else View.GONE
        note.text = ctx.getString(R.string.pending_note)

        val box = v.findViewById<LinearLayout>(R.id.sources)
        box.removeAllViews()
        box.visibility = if (m.sources.isEmpty()) View.GONE else View.VISIBLE
        for (s in m.sources) box.addView(sourceView(box, s))

        v.setOnClickListener(m.retryQuestion?.let { q -> View.OnClickListener { onRetry(q) } })
    }

    /** 출처 한 줄: 제목 · 수집일, 메뉴 경로, '원문 보기 ↗' (FR-004, FR-007, FR-022) */
    private fun sourceView(parent: ViewGroup, s: Source): View {
        val ctx = parent.context
        val tv = TextView(ctx)
        val muted = ContextCompat.getColor(ctx, R.color.muted)
        val navy = ContextCompat.getColor(ctx, R.color.navy)
        val sb = SpannableStringBuilder()
        val label = if (s.kind == "학과 조교 답변") "학과 조교 답변" else "출처"
        sb.append("$label: ${s.title}")
        s.collectedAt?.let { sb.append(" · ${it.take(10)}") }
        s.menuPath?.let { sb.append("\n위치: $it") }
        sb.setSpan(ForegroundColorSpan(muted), 0, sb.length, 0)
        if (s.url != null) {
            val start = sb.length
            sb.append("\n원문 보기 ↗")
            sb.setSpan(ForegroundColorSpan(navy), start, sb.length, 0)
            sb.setSpan(StyleSpan(Typeface.BOLD), start, sb.length, 0)
            tv.setOnClickListener { ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(s.url))) }
        }
        tv.text = sb
        tv.textSize = 12f
        tv.setPadding(0, 6, 0, 6)
        return tv
    }
}
