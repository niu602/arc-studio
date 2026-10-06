package com.voice.calendar.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.voice.calendar.entity.ScheduleCommand;
import okhttp3.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

@Service
public class DoubaoService {
    //密钥
    @Value("${doubao.api-key}")
    private String apiKey;

    // 模型端点ID
    private static final String ENDPOINT_ID = "ep-m-20260531081452-qn8n8";
    //网络请求工具
    private final OkHttpClient okHttpClient;
    //JSON解析工具
    private final ObjectMapper objectMapper;
    //AI输出的指令规则
    private static final String PROMPT_TEMPLATE =
            "你是专业日程指令解析助手，仅负责把用户自然语言转为标准JSON，严格遵守格式与规则。\n" +
                    "输出固定结构：\n" +
                    "{\n" +
                    "  \"action\": \"操作类型\",\n" +
                    "  \"startTime\": \"开始时间(yyyy-MM-dd HH:mm)\",\n" +
                    "  \"endTime\": \"结束时间(yyyy-MM-dd HH:mm)\",\n" +
                    "  \"content\": \"日程内容关键词\",\n" +
                    "  \"location\": \"日程地点\"\n" +
                    "}\n\n" +
                    "【强制规则】\n" +
                    "1. action 仅允许取值：add(添加)、delete(删除)、query(查询)、update(修改)，识别不出指令固定返回 unknown。\n" +
                    "2. 所有时间统一转为 yyyy-MM-dd HH:mm 格式，基准日期：%s。\n" +
                    "3. 时间语义转换规则：\n" +
                    "   - 今天 → startTime=今日00:00，endTime=今日23:59\n" +
                    "   - 明天 → startTime=明日00:00，endTime=明日23:59\n" +
                    "   - 本周 → 本周一00:00 至 本周日23:59\n" +
                    "   - 单独时间点（如明天下午3点）→ 该时间作为 startTime，无明确结束时间则 endTime = startTime + 1小时\n" +
                    "4. 各操作解析细则：\n" +
                    "   【query 查询】：按时间范围+内容筛选日程，无内容则 content=null，无地点则 location=null。\n" +
                    "   【delete 删除】：\n" +
                    "     - 指定时间+内容：填充对应时间与内容；\n" +
                    "     - 删除全部XX：startTime=null、endTime=null，仅保留 content；\n" +
                    "     - 删除全部日程：startTime=null、endTime=null、content=null、location=null。\n" +
                    "   【add 添加】：必须提取日程内容、时间；无地点 location=null；无结束时间自动顺延1小时。\n" +
                    "   【update 修改】：提取原日程时间/内容作为筛选条件，保留原有字段规则。\n" +
                    "5. 字段填空规则：未提及内容、地点，对应字段设为 null；禁止填空字符串。\n" +
                    "6. 输出要求：**只返回纯JSON文本**，严禁添加解释、注释、Markdown、多余换行、语气词。\n" +
                    "7. 识别失败、指令无关、语义混乱时，固定返回：{\"action\":\"unknown\",\"startTime\":null,\"endTime\":null,\"content\":null,\"location\":null}\n\n" +
                    "用户指令：%s";


    public DoubaoService() {
        this.okHttpClient = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .build();//设置超时时间，防止卡死
        this.objectMapper = new ObjectMapper();
    }

    /**
     * 解析自然语言指令为结构化日程命令
     */
    public ScheduleCommand parseCommand(String userCommand) throws IOException {
        // 获取今天的日期
        String today = java.time.LocalDate.now().toString();

        // 构建完整的Prompt
        String prompt = String.format(PROMPT_TEMPLATE, today, userCommand);

        // 构建正确的请求体（火山方舟要求的格式）
        String requestBody = String.format(
                "{\"model\":\"%s\",\"messages\":[{\"role\":\"user\",\"content\":\"%s\"}],\"temperature\":0.1,\"max_tokens\":1024}",
                ENDPOINT_ID, prompt.replace("\"", "\\\"").replace("\n", "\\n")
        );

        // 构建请求
        Request request = new Request.Builder()
                .url("https://ark.cn-beijing.volces.com/api/v3/chat/completions")
                .addHeader("Authorization", "Bearer " + apiKey)
                .addHeader("Content-Type", "application/json")
                .post(RequestBody.create(requestBody, MediaType.parse("application/json")))
                .build();

        // 发送请求并打印详细错误信息（方便调试）
        try (Response response = okHttpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errorBody = response.body().string();
                throw new RuntimeException("豆包API调用失败：" + response.code() + " " + response.message() + "\n错误详情：" + errorBody);
            }

            // 解析返回结果
            String responseBody = response.body().string();
            JsonNode root = objectMapper.readTree(responseBody);
            String content = root.get("choices").get(0).get("message").get("content").asText().trim();

            // 清理可能的markdown格式（如果大模型不小心输出了```json）
            if (content.startsWith("```json")) {
                content = content.substring(7, content.length() - 3).trim();
            }

            // 将JSON转换为ScheduleCommand对象
            return objectMapper.readValue(content, ScheduleCommand.class);
        }
    }
}