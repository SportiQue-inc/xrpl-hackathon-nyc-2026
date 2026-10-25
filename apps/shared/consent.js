// 연구 참여 동의서. 요청 하나마다 연구 참여 설명·동의(생명윤리법 제16조)와 개별 동의
// (제3자 제공: 개인정보 보호법 제17조 제2항, 민감정보: 제23조, 국외 이전: 제28조의8)를 각각 한 장씩 만듭니다.
// 각 장의 본문 해시가 서명하는 statement에 들어가므로, 참여자가 읽은 글과 서명이 묶입니다.

import { UNIT } from "./ui.js";
const won = (x) => `${(Math.round((x || 0) * 100) / 100).toFixed(2)} ${UNIT}`;

export async function textHash(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// r: request card, send: the items picked ({item, label, weeks, sensitive}), price: the payment for them,
// names: {org, purpose, item(i), weeks(ws)}
export function consentPages(r, send, price, names) {
  const { org, purpose, item, weeks } = names;
  const allWeeks = weeks(send.flatMap((i) => i.weeks));
  const itemLines = send.map((i) => `· ${item(i.item)}: ${weeks(i.weeks)}`);
  const pay = r.payment || { immediate_pct: 80, held_pct: 20, review: "7 days" };
  const reviewDays = String(pay.review || "7 days").replace(/\D+/g, "") || "7";
  const bonus = r.completion_bonus_xrp ? `모든 회차를 마치면 완료 보너스 ${won(r.completion_bonus_xrp)}를 추가로 드립니다. 철회하면 완료 보너스는 지급되지 않습니다.` : null;
  const abroad = r.international_transfer && r.international_transfer.planned ? r.international_transfer : null;
  const health = send.map((i) => item(i.item)).join(", ");

  const pages = [
    {
      kind: "research", title: "연구 참여 설명 및 동의", basis: "생명윤리 및 안전에 관한 법률 제16조",
      sections: [
        ["1. 연구 목적", `${org}이(가) 수행하는 ${purpose}입니다. 참여자가 동의한 주간 건강 기록을 모아 분석합니다.`],
        ["2. 참여 방법", [`연구 기관이 요청한 회차에, 동의한 항목만 전달됩니다. 방문이나 검사는 없습니다.`, ...itemLines]],
        ["3. 예상 위험과 이익", "신체적 위험은 없습니다. 기록이 전달되는 과정에서 정보가 노출될 위험이 있어, 이름 대신 참여 번호를 쓰고 암호화해 전달합니다. 참여에 따른 직접적인 의학적 이익은 없습니다."],
        ["4. 참여 지급", [
          `이번 요청의 참여 지급액은 ${won(price)}입니다.`,
          `회차마다 기록이 전달되면 ${pay.immediate_pct}%가 지급되고, ${pay.held_pct}%는 ${reviewDays}일 검토 후 지급됩니다.`,
          "지급액은 전달 전에 원장에 예치되며, 기록이 전달되어야 풀립니다.",
          "검토 후 지급분은 위조 데이터, 다른 사람의 기기·데이터 사용, 여러 계정 사용이 확인된 경우에만 지급되지 않습니다. 이 경우 미리 이유를 알리고 소명할 기회를 드립니다.",
          bonus,
        ].filter(Boolean)],
        ["5. 개인정보 제공", "연구 기관은 참여 번호와 동의한 항목만 받습니다. 이름, 연락처, 식별번호는 받지 않습니다. 참여 번호와 본인을 잇는 정보는 참여자의 에이전트에만 있습니다."],
        ["6. 동의 철회", "언제든 철회할 수 있으며, 철회해도 불이익은 없습니다. 철회하면 아직 전달되지 않은 회차는 멈추고 예치금은 연구로 돌아갑니다. 연구 기관은 개인 단위 사본을 파기하고 확인해야 합니다. 이미 만들어진 집계 통계만 남습니다. 이미 받은 지급액은 그대로입니다."],
        ["7. 다른 연구 이용", "식별 정보를 지운 자료라도 다른 연구에는 쓰지 않습니다."],
        ["8. 연구 심의", `기관생명윤리위원회(IRB) 승인: ${r.ethics_approval || "확인 중"}. 승인 사실은 원장의 자격 증명으로 확인됩니다.`],
        ["9. 기록 보관", "접근 기록은 2년, 권한 변경 기록은 3년 보관합니다."],
      ],
      agree: "연구 참여 설명을 끝까지 읽고 이해했으며, 자발적으로 참여에 동의합니다.",
    },
    {
      kind: "third_party", title: "개인정보 제3자 제공 동의", basis: "개인정보 보호법 제17조 제2항",
      sections: [
        ["제공받는 자", org],
        ["이용 목적", purpose],
        ["제공 항목", [...itemLines, "· 참여 번호(이름·연락처 제외)"]],
        ["보유·이용 기간", `연구 종료 시까지. 철회하면 지체 없이 파기하고 파기 사실을 확인합니다.`],
        ["동의를 거부할 권리", "동의를 거부할 수 있습니다. 거부하면 이번 요청에는 참여할 수 없지만, 앱 이용과 다른 연구 참여에는 불이익이 없습니다."],
      ],
      agree: "위 내용으로 개인정보를 제3자에게 제공하는 데 동의합니다.",
    },
    {
      kind: "sensitive", title: "민감정보(건강정보) 처리 동의", basis: "개인정보 보호법 제23조 제1항 제1호",
      sections: [
        ["처리하는 민감정보", `건강정보: ${health}`],
        ["처리 목적", `${purpose}에서 회차별 기록 분석`],
        ["기간", allWeeks],
        ["보유·이용 기간", "연구 종료 시까지. 철회하면 지체 없이 파기합니다."],
        ["동의를 거부할 권리", "다른 동의와 별도로 받는 동의이며, 거부할 수 있습니다. 거부하면 이 항목은 보내지 않습니다."],
      ],
      agree: "건강정보 처리에 다른 동의와 별도로 동의합니다.",
    },
  ];
  if (abroad) {
    pages.push({
      kind: "international", title: "개인정보 국외 이전 동의", basis: "개인정보 보호법 제28조의8 제2항",
      sections: [
        ["이전되는 항목", itemLines],
        ["이전 국가·시기·방법", `${(abroad.countries || []).join(", ")} · 회차별 전달 시 · 암호화해 네트워크로 전송`],
        ["이전받는 자", (abroad.recipients || []).join(", ")],
        ["이용 목적·보유 기간", `${abroad.purpose || purpose} · ${abroad.retention || "연구 종료 시까지"}`],
        ["거부 방법과 효과", "동의를 거부할 수 있으며, 거부하면 국외 기관은 기록을 받지 않습니다. 설정에서 언제든 철회할 수 있습니다."],
      ],
      agree: "개인정보의 국외 이전에 별도로 동의합니다.",
    });
  }
  return pages.map((p) => ({ ...p, text: plain(p) }));
}

// The exact text the person reads, hashed into the signed statement.
function plain(p) {
  return [p.title, p.basis, ...p.sections.map(([h, v]) => `${h}\n${Array.isArray(v) ? v.join("\n") : v}`), p.agree].join("\n\n");
}
