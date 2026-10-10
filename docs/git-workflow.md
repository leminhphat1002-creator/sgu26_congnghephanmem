# Quy ước Git

## Nhánh

```
main  ◀── develop  ◀── feature/*
(deploy)   (tích hợp)    (mỗi việc một nhánh)
```

- `main`: luôn ở trạng thái chạy được; Tuần 6 trở đi, CI xanh trên `main` kích hoạt CD.
- `develop`: nhánh tích hợp; mọi `feature/*` merge vào đây trước.
- `feature/*`: đặt tên `feature/tuan-<số>-<người>-<việc>`, ví dụ `feature/tuan-2-a-poi-data`.
- **Không push thẳng** vào `main` hay `develop`. Mọi thay đổi đi qua Pull Request.

## Quy trình mỗi tuần

1. A: `git checkout develop && git pull`, tạo nhánh `feature/...`, làm, chạy test, mở PR vào
   `develop`, B review, merge.
2. B: chỉ bắt đầu sau khi pull phần A đã tích hợp vào `develop`; làm, mở PR, A review, merge.
3. Cuối tuần, khi `develop` ổn định, mở PR `develop` → `main` (cần CI xanh và 1 review).

## Pull Request và review chéo

- Mọi PR cần ít nhất 1 review của thành viên còn lại, điền checklist trong
  `.github/pull_request_template.md`.
- Người review kiểm tra: đúng 3 lớp (xem `docs/kien-truc-3-lop.md`), có test, không commit secret.
- Khi bật branch protection (Tuần 5): bắt buộc status check `lint`, `test-backend` và 1 review.

## Quy tắc cấm

- Không `git push --force`, không sửa lịch sử đã push để ghép việc.
- Không commit `.env`, `*.db`, MP3, thư mục `data/` hay `audio_files/`.

## Mẫu commit message

Dạng `<loại>(<phạm vi>): <mô tả ngắn, thể mệnh lệnh>`

| Loại | Dùng khi |
| --- | --- |
| `feat` | thêm tính năng |
| `fix` | sửa lỗi |
| `test` | thêm hoặc sửa test |
| `docs` | tài liệu |
| `refactor` | đổi cấu trúc, không đổi hành vi |
| `ci` | workflow CI/CD, Docker |
| `chore` | việc lặt vặt (cấu hình, dọn dẹp) |

Ví dụ: `feat(poi): thêm Haversine và find_nearby`, `ci: thêm job build-docker`.

Phần thân (tùy chọn) giải thích *vì sao* đổi, không chỉ *đổi gì*.
