# Codex Static App

Codex에서 제작한 정적 HTML 앱을 GitHub와 Vercel로 배포하기 위한 저장소입니다.

## Main App

- Entry: `index.html`
- Primary screen: `pop_weight_interface.html`

## Local Preview

정적 파일이므로 별도 빌드 없이 브라우저에서 `index.html`을 열어 확인할 수 있습니다.

간단한 로컬 서버로 확인하려면 다음 명령을 사용할 수 있습니다.

```bash
python3 -m http.server 5173
```

이후 `http://localhost:5173`으로 접속합니다.

## Vercel Deployment

1. GitHub에 이 저장소를 push합니다.
2. Vercel Dashboard에서 **Add New Project**를 선택합니다.
3. GitHub 저장소를 import합니다.
4. Framework Preset은 `Other` 또는 자동 감지값을 사용합니다.
5. Build Command는 비워두고, Output Directory도 기본값을 사용합니다.
6. 배포 후 생성된 Production URL에서 앱을 확인합니다.

## Notes

- 민감한 값은 `.env`에 저장하고 GitHub에는 커밋하지 않습니다.
- 현재 앱은 정적 HTML 기반이므로 Vercel 환경변수는 필요하지 않습니다.
