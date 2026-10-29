# Publish to your GitHub

The files in this archive form a **new independent repository**. Do **not** put the files in an unrelated existing project.

1. Sign in to GitHub and create a **public** repository called `data-center-capacity-intelligence` (choose **no** automatically created README, .gitignore, or license because they are included here).
2. Unzip the project on your computer and open a terminal in its root directory (the directory containing `README.md` and `compose.yaml`).
3. Run:

```bash
git init
git branch -M main
git add .
git commit -m "Initial public Azure VM capacity analytics project"
git remote add origin https://github.com/Inkyungkimm/data-center-capacity-intelligence.git
git push -u origin main
```

4. Update GitHub repository description to: `End-to-end capacity analytics engineering using Microsoft's public Azure traces, Python, PostgreSQL, dbt, and Streamlit.`
5. After running the **real** source ingestion and `dbt build`, add trustworthy screenshots to the README. Do not add fabricated results or upload the proprietary data of a workplace or client.

## 주의

- 신규 리포지토리를 직접 만들어야 합니다. 이 ZIP에 든 파일은 아직 GitHub에 게시되지 않았습니다.
- 실제 Azure 원본 데이터는 대용량이라 저장소에 포함하지 않았습니다. 실행 시 공식 배포 링크에서 다운로드합니다.
- `raw_data/` 및 `.env`는 `.gitignore`에 포함되어 있습니다.
- 공개 데이터는 Microsoft의 CC BY 조건에 따라 출처를 표시해야 합니다. 이 저장소의 코드 라이선스와 별개입니다.
