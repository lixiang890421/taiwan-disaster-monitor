# Taiwan Disaster Monitor

臺灣災害監控系統雛形。

## 功能

- 全台 22 縣市狀態卡片
- 首頁重大警示跑馬燈
- 縣市下拉式篩選
- 人事行政總處停班停課監控
- 中央氣象署海嘯資訊監控
- 臺南市政府新聞監控
- 臺南災害應變告示網監控

## Docker 執行

```bash
docker build -t taiwan-disaster-monitor .
docker run -d \
  --name disaster-dashboard \
  --restart unless-stopped \
  -p 8088:8080 \
  -e TZ=Asia/Taipei \
  -v $(pwd)/data:/data \
  taiwan-disaster-monitor
cd /volume1/docker/disaster-bot

cat > requirements.txt <<'EOF'
flask
requests
beautifulsoup4
gunicorn
