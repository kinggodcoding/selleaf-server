from django.db import transaction
from django.db.models import F, CharField, Value, Q
from django.db.models.functions import Concat
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from rest_framework.response import Response
from rest_framework.views import APIView

from apply.models import Apply, Trainee
from lecture.models import Lecture, LectureReview
from member.models import Member
from notice.models import Notice
from qna.models import QnA
from teacher.models import Teacher


# 관리자 로그인
class ManagerLoginView(View):
    # 관리자 로그인 페이지 이동 뷰
    def get(self, request):
        # 로그인 한 상태에서 다시 로그인 페이지에 접근하려 했는지 검사
        if request.session.get('admin') is not None:
            # 만약 그렇다면 회원 정보 리스트 페이지로 redirect
            return redirect('manager-member')

        # 로그인이 안 되어있던 상태라면 로그인 페이지로 이동
        return render(request, 'manager/login/login.html')

    # 관리자 로그인 버튼 누른 후의 뷰
    def post(self, request):
        # 로그인 정보를 가져옴
        data = request.POST

        # 관리자 로그인 정보도 'admin' 이라는 키로 세션에 저장
        request.session['admin'] = data

        # 이전에 요청한 관리자 페이지 내 경로가 있다면 변수에 담음
        previous_uri = request.session.get('previous_uri')

        # 따로 요청한 경로가 없을 때에는 회원 관리 페이지로 이동
        path = 'manager-member'

        # 만약 따로 요청한 페이지가 있었다면
        if previous_uri is not None:
            # 이동하려고 하는 경로를 요청한 페이지로 지정
            path = previous_uri

            # 원래 요청했던 페이지에 대한 정보는 세션에서 제거
            del request.session['previous_uri']

        # 위 분기에 따라 결정된 페이지로 이동
        # 기본적으로는 회원 관리 페이지
        return redirect(path)


# 관리자 로그아웃
class ManagerLogoutView(View):
    def get(self, request):
        # 세션 정보 전체 초기화
        request.session.clear()

        # 관리자 로그인 페이지로 이동
        return redirect('manager-login')


# 회원 관리
class MemberManagementView(View):
    # 회원관리 페이지 이동 뷰
    def get(self, request):
        # 현재 가입한 회원 수(휴면 + 비휴면)
        member_count = Member.objects.count()

        # 화면에 보내기 전에 dict 데이터로 만들어 줌
        context = {'member_count': member_count}

        # member.html을 불러오면서 화면에 회원 수 전달
        return render(request, 'manager/member/member/member.html',context)


class MemberInfoAPI(APIView):
    def get(self, request, page):
        # 한 페이지에 띄울 회원 수
        row_count = 10

        # 한 페이지에 표시할 회원 정보들을 슬라이싱 하기 위한 변수들
        offset = (page - 1) * row_count
        limit = page * row_count

        # 회원 정보 표시에 필요한 tbl_member와 tbl_member_address의 컬럼들
        columns = [
            'id',
            'member_name',
            'member_email',
            'member_address',
            'member_type',
            'member_status'
        ]

        # 최근에 가입한 순서대로 10명의 회원을 가져옴
        # 기존에 tbl_member에 없던 주소는 tbl_member_address에서 가져와서 문자열 합치기
        members = Member.objects\
                      .annotate(member_address=Concat(F('memberaddress__address_city'),
                                                      Value(" "),
                                                      F('memberaddress__address_district'),
                                                      output_field=CharField()
                                                      )
                                )\
                      .values(*columns)[offset:limit]

        # 다음 페이지에 띄울 정보가 있는지 검사
        has_next_page = Member.objects.filter()[limit:limit + 1].exists()

        # 완성된 회원정보 목록
        member_info = {
            'members': members,
            'hasNext': has_next_page,
        }

        return Response(member_info)


class DeleteManyMembersAPI(APIView):
    # 한 번에 여러 명의 회원을 휴면상태로 변경하는 뷰
    def patch(self, request, member_ids):
        # 요청 경로에 담긴 member_ids를 콤마(,)를 기준으로 분리해서 list로 만듬
        member_ids = member_ids.split(',')

        # 위 list의 각 요소를 순회
        for member_id in member_ids:
            # 요소가 빈 문자열이 아닐 때만 tbl_member에서 해당 id를 가진 객체를 가져옴
            if member_id != '':
                member = Member.objects.get(id=member_id)

                # 해당 객체의 status를 1(휴면)으로 만들고, 변경 시간과 같이 저장
                member.member_status = 1
                member.updated_date = timezone.now()
                member.save(update_fields=["member_status", "updated_date"])

        return Response('성공')



# 강사 관리
class TeacherManagementView(View):
    # 강사 관리 페이지 이동 뷰
    def get(self, request):
        # 현재 강사 수
        teachers = Teacher.enabled_objects.count()

        # 강사 신청자 수
        teacher_entries = Teacher.objects.filter(teacher_status=0).count()

        # 강사 수를 화면에서 쓸 수 있게 dict 형태로 만들어줌
        context = {
            "teachers": teachers,
            "teacher_entries": teacher_entries
        }

        # 위의 dict 데이터를 teacher.html에 실어서 보냄
        return render(request, 'manager/teacher/teacher.html', context)


class TeacherEntryManagementView(View):
    # 강사 신청자 관리 페이지 이동 뷰
    def get(self, request):
        # 현재 강사 수
        teachers = Teacher.enabled_objects.count()

        # 강사 신청자 수
        teacher_entries = Teacher.objects.filter(teacher_status=0).count()

        print(teachers, teacher_entries)

        # 강사 수를 화면에서 쓸 수 있게 dict 형태로 만들어줌
        context = {
            "teachers": teachers,
            "teacher_entries": teacher_entries
        }

        # 위의 dict 데이터를 teacher-entries.html에 실어서 보냄
        return render(request, 'manager/teacher/teacher-entries.html', context)


class TeacherInfoAPI(APIView):
    # 강사 정보를 가져오는 API 뷰
    def get(self, request, page):
        # 한 페이지에 띄울 강사 수
        row_count = 10

        # 한 페이지에 표시할 강사 정보들을 슬라이싱 하기 위한 변수들
        offset = (page - 1) * row_count
        limit = page * row_count

        # 강사 정보 표시에 필요한 tbl_member와 tbl_teacher의 컬럼들
        columns = [
            'id',
            'teacher_name',
            'teacher_info',
            'lecture_plan',
            'created_date',
        ]

        # 최근에 승인된 순으로 강사 10명의 정보를 가져옴
        teachers = Teacher.enabled_objects.annotate(teacher_name=F('member__member_name'))\
            .values(*columns).order_by('-id')[offset:limit]

        # 다음 페이지에 띄울 정보가 있는지 검사
        has_next_page = Teacher.enabled_objects.filter()[limit:limit + 1].exists()

        # 각각의 강사 정보에서 created_date를 "YYYY.MM.DD" 형식으로 변환
        for teacher in teachers:
            teacher['created_date'] = teacher['created_date'].strftime('%Y.%m.%d')

        # 완성된 강사 정보 목록
        teacher_info = {
            'teachers': teachers,
            'hasNext': has_next_page,
        }

        # 요청한 데이터 반환
        return Response(teacher_info)


class TeacherEntriesInfoAPI(APIView):
    # 강사 신청자 정보를 가져오는 API 뷰
    def get(self, request, page):
        # 한 페이지에 띄울 신청자 수
        row_count = 10

        # 한 페이지에 표시할 신청자 정보들을 슬라이싱 하기 위한 변수들
        offset = (page - 1) * row_count
        limit = page * row_count

        # 신청자 정보 표시에 필요한 tbl_member와 tbl_teacher의 컬럼들
        columns = [
            'id',
            'teacher_name',
            'teacher_info',
            'lecture_plan',
            'created_date',
        ]

        # 최근에 승인된 순으로 신청자 10명의 정보를 가져옴
        teacher_entries = Teacher.objects.filter(teacher_status=0).annotate(teacher_name=F('member__member_name'))\
            .values(*columns).order_by('-id')[offset:limit]

        # 다음 페이지에 띄울 정보가 있는지 검사
        has_next_page = Teacher.objects.filter(teacher_status=0)[limit:limit + 1].exists()

        # 각각의 신청자 정보에서 created_date를 "YYYY.MM.DD" 형식으로 변환
        for teacher_entry in teacher_entries:
            teacher_entry['created_date'] = teacher_entry['created_date'].strftime('%Y.%m.%d')

        # 완성된 신청자 정보 목록
        # 위의 강사 목록과 showTeachers 모듈을 공유하기 위해 키를 'teachers' 로 설정함
        teacher_info = {
            'teachers': teacher_entries,
            'hasNext': has_next_page,
        }

        # 요청한 데이터 반환
        return Response(teacher_info)


class TeacherApprovalAPI(APIView):
    # 강사 여러 명 승인 API 뷰
    def patch(self, request, teacher_ids):
        # 요청 경로에 담긴 teacher_ids를 콤마(,)를 기준으로 분리해서 list로 만듬
        teacher_ids = teacher_ids.split(',')

        # 위 list의 각 요소를 순회
        for teacher_id in teacher_ids:
            # 요소가 빈 문자열이 아닐 때만 tbl_teacher에서 해당 id를 가진 객체를 가져옴
            if teacher_id != '':
                teacher = Teacher.objects.get(id=teacher_id)

                # 해당 객체의 status를 1(승인)으로 만들고, 변경 시간과 같이 저장
                teacher.teacher_status = 1
                teacher.updated_date = timezone.now()
                teacher.save(update_fields=["teacher_status", "updated_date"])

        return Response('성공')


class TeacherDeleteAPI(APIView):
    # 강사 여러 명 차단 API 뷰
    def patch(self, request, teacher_ids):
        # 요청 경로에 담긴 teacher_ids를 콤마(,)를 기준으로 분리해서 list로 만듬
        teacher_ids = teacher_ids.split(',')

        # 위 list의 각 요소를 순회
        for teacher_id in teacher_ids:
            # 요소가 빈 문자열이 아닐 때만 tbl_teacher에서 해당 id를 가진 객체를 가져옴
            if teacher_id != '':
                teacher = Teacher.objects.get(id=teacher_id)

                # 해당 객체의 status를 1(승인)으로 만들고, 변경 시간과 같이 저장
                teacher.teacher_status = 1
                teacher.updated_date = timezone.now()
                teacher.save(update_fields=["teacher_status", "updated_date"])

        return Response('성공')


# 게시물 관리
class PostManagementView(View):
    # 게시물 관리 페이지 이동 뷰
    def get(self, request):
        # 모든 게시물(커뮤니티, 노하우, 거래) 정보 다 들고 가기
        return render(request, 'manager/post/post.html')

    # 게시물 삭제를 위한 뷰
    def post(self, request):
        # status를 변경할 게시물들의 정보를 가져와야 됨
        return render(request, 'manager/post/post.html')


# 강의 관리
class LectureManagementView(View):
    # 강의 관리 페이지 이동 뷰
    def get(self, request):
        # 강의 게시물 전체 개수
        lecture_count = Lecture.objects.filter(lecture_status=0).count()
        
        # 강의 게시물 수를 context에 담음
        context = {'lecture_count': lecture_count}
        
        # lecture.html 페이지로 이동
        return render(request, 'manager/lecture/lecture/lecture.html', context)


class LectureInfoAPI(APIView):
    # 개설된 강의 정보를 가져오는 API 뷰
    def get(self, request, page):
        # 한 페이지에 띄울 강의 수
        row_count = 10

        # 한 페이지에 표시할 강의 정보들을 슬라이싱 하기 위한 변수들
        offset = (page - 1) * row_count
        limit = page * row_count

        # 강의 정보 표시에 필요한 컬럼들
        columns = [
            'id',
            'lecture_title',
            'lecture_content',
            'teacher_name',
            'lecture_headcount',
            'lecture_price',
            'lecture_place',
            'online_status',
            'created_date',
        ]

        # 강의 게시글 10개의 정보를 최신순으로 가져옴
        lectures = Lecture.objects.filter(lecture_status=0)\
                       .annotate(teacher_name=F('teacher__member__member_name'),
                                 lecture_place=Concat(F('lectureaddress__address_city'),
                                                      Value(" "),
                                                      F('lectureaddress__address_district'),
                                                      output_field=CharField()
                                                      ),
                                )\
                       .values(*columns)[offset:limit]

        # 다음 페이지에 띄울 정보가 있는지 검사
        has_next_page = Lecture.objects.filter(lecture_status=0)[limit:limit + 1].exists()

        # 각각의 강의 정보에서 created_date를 "YYYY.MM.DD" 형식으로 변환
        for lecture in lectures:
            lecture['created_date'] = lecture['created_date'].strftime('%Y.%m.%d')

            # 아래의 for문에서 각 강의 별 수강생 수를 담을 변수
            total_trainees = 0

            # 각 강의 별 수강생 수 추가하기
            # 해당 강의 신청 내역들 -> 각 신청 내역들의 인원 수의 총 합계
            # 강의 신청 내역 조건
            apply_condition_vaild = Q(apply_status=0) | Q(apply_status=1)
            apply_condition_lecture = Q(lecture_id=lecture['id'])
            apply_condition = apply_condition_lecture & apply_condition_vaild

            # 위 조건식으로 해당 강의를 신청한 내역 전체를 조회
            applies = Apply.objects.filter(apply_condition)

            # 각 신청 내역 별 인원 수를 총합에 더함
            for apply in applies:
                trainee_count = Trainee.objects.filter(apply=apply.id).count()
                total_trainees += trainee_count

            # 각 강의(dict)에 신청자 수를 담을 키 생성
            lecture['total_trainees'] = total_trainees

        # 완성된 강의 정보 목록
        lecture_info = {
            'lectures': lectures,
            'hasNext': has_next_page,
        }

        # 요청한 데이터 반환
        return Response(lecture_info)


# 강의 리뷰 관리
class LectureReviewManagementView(View):
    # 강의 리뷰 관리 페이지 이동 뷰
    def get(self, request):
        # 특정 강의에 대한 리뷰 정보 필요 - 쿼리 스트링에 요청
        lecture = Lecture.objects.get(id=request.GET['id'])

        # 강의 게시글 리뷰 개수
        review_count = lecture.lecturereview_set.count()

        # 강의 수강생 수 구하기 - 해당 강의 신청 내역들 -> 각 신청 내역들의 동행자 수의 총 합계
        # 강의 신청 내역 조건
        apply_condition_vaild = Q(apply_status=0) | Q(apply_status=1)
        apply_condition_lecture = Q(lecture_id=lecture.id)
        apply_condition = apply_condition_lecture & apply_condition_vaild

        # 위 조건식으로 해당 강의를 신청한 내역 전체를 조회
        applies = Apply.objects.filter(apply_condition)

        # 아래의 for문으로 구한 총 신청자 수를 담을 변수
        total_trainees_count = 0

        # 각 신청 내역의 신청자 수 구하기
        for apply in applies:
            trainees_count = Trainee.objects.filter(apply=apply.id).count()

            # 수강생 이름 확인
            # trainees = Trainee.objects.filter(apply=apply.id).order_by('id')
            #
            # for trainee in trainees:
            #     print(trainee.trainee_name)

            # 총 신청자 수 합계에 더하기
            total_trainees_count += trainees_count

        # 강의 정보와 리뷰 개수, 신청자 수를 dict에 담음
        context = {
            'lecture': lecture,
            'review_count': review_count,
            'trainees_count': total_trainees_count
        }

        # 아래의 html 페이지로 이동
        return render(request, 'manager/lecture/lecture-detail/lecture-detail-review.html', context)


class LectureReviewInfoAPI(APIView):
    # 특정 강의에 달린 리뷰 목록을 가져오는 뷰
    def get(self, request, lecture_id, page):
        # 한 페이지에 띄울 리뷰 개수
        row_count = 10

        # 한 페이지에 표시할 리뷰 정보들을 슬라이싱 하기 위한 변수들
        offset = (page - 1) * row_count
        limit = page * row_count

        # 리뷰 정보 표시에 필요한 컬럼들
        columns = [
            'id',
            'review_title',
            'review_content',
            'member_name',
            'review_rating',
            'created_date',
        ]

        # 특정 강의의 리뷰 10개를 최신순으로 가져옴
        reviews = LectureReview.objects.filter(lecture=lecture_id)\
            .annotate(member_name=F('member__member_name'))\
            .values(*columns)[offset:limit]

        # 다음 페이지에 띄울 정보가 있는지 검사
        has_next_page = LectureReview.objects.filter(lecture=lecture_id)[limit:limit + 1].exists()

        # 각각의 강의 정보에서 created_date를 "YYYY.MM.DD" 형식으로 변환
        for review in reviews:
            review['created_date'] = review['created_date'].strftime('%Y.%m.%d')

        # 완성된 리뷰 목록
        lecture_review_info = {
            'reviews': reviews,
            'hasNext': has_next_page
        }

        # 요청한 데이터 반환
        return Response(lecture_review_info)


# 댓글 관리
class ReplyManagementView(View):
    # 댓글 관리 페이지 이동 뷰
    def get(self, request):
        # 모든 게시물에 대한 댓글을 전부 가져와야 됨
        return render(request, 'manager/comment/comment.html')

    # 특정 댓글 삭제를 위한 뷰
    def post(self, request):
        # 특정 댓글들 status 변경
        return render(request, 'manager/comment/comment.html')


# 태그 관리
class TagManagementView(View):
    # 태그 관리 페이지 이동 뷰
    def get(self, request):
        # 모든 게시물에 대한 댓글을 전부 가져와야 됨
        return render(request, 'manager/tag/tag.html')

    # 특정 태그 삭제를 위한 뷰
    def post(self, request):
        # 태그들 status 변경
        return render(request, 'manager/tag/tag.html')


# 결제 내역 관리
class PaymentManagementView(View):
    # 결제 내역 관리 페이지 이동 뷰
    def get(self, request):
        # 모든 결제 내역과, 각 결제 내역의 회원, 상품 내역 전부 가져와야 됨
        return render(request, 'manager/payment/payment.html')


# 공지사항 관리
class NoticeManagementView(View):
    # 공지사항 내역 페이지 이동 뷰
    def get(self, request):
        # 현재 작성된 공지사항 및 QnA의 개수를 세서 dict 데이터로 통합
        notice_count = Notice.enabled_objects.count()
        qna_count = QnA.enabled_objects.count()

        context = {
            'notice_count': notice_count,
            'qna_count': qna_count
        }

        # 공지사항과 QnA 개수를 화면에 전달
        # 공지사항 내역을 가져오는 것은 별도의 API가 해줌
        return render(request, 'manager/manager-notice/manager-notice/manager-notice.html', context)


class WriteNoticeView(View):
    # 공지사항 작성 페이지 이동 뷰
    def get(self, request):
        # 로그인 검사는 미들웨어가 해주기 때문에, 별도의 정보 필요 없이 바로 render
        return render(request, 'manager/manager-notice/manager-notice/manager-notice-compose.html')

    # 공지사항 작성 완료 이후의 뷰
    @transaction.atomic
    def post(self, request):
        # POST 방식으로 요청한 데이터를 가져옴
        notice_data = request.POST

        # 받아온 데이터에서 특정 정보(id, 제목, 내용)를 가져와서 dict 타입으로 저장
        data = {
            'notice_title': notice_data['notice-title'],
            'notice_content': notice_data['notice-content'],
        }

        # 받아온 데이터로 tbl_notice에 실행할 insert 쿼리 작성
        Notice.objects.create(**data)

        # 작성한 공지사항 저장 후, 공지사항 리스트 페이지로 redirect
        return redirect('manager-notice')


class UpdateNoticeView(View):
    # 공지사항 수정 페이지 이동 뷰
    def get(self, request):
        # 수정 버튼에서 전달한 id를 통해 수정할 공지사항 객체 가져오기
        notice = Notice.objects.get(id=request.GET['id'])

        # 수정 페이지에 전달할 공지사항의 dict 타입의 데이터 생성
        context = {
            'notice': notice
        }

        # 공지사항 데이터를 가지고 수정 페이지로 이동
        return render(request, 'manager/manager-notice/manager-notice/manager-notice-modify.html', context)

    # 공지사항 수정 완료 이후의 뷰
    @transaction.atomic
    def post(self, request):
        # GET 방식으로 url에서 id를 가져옴
        notice_id = request.GET['id']

        # POST 방식으로 받은 id와 제목과 내용도 가져옴
        data = request.POST

        data = {
            'notice_title': data['notice-title'],
            'notice_content': data['notice-content']
        }

        # 가져온 id로 수정할 공지사항 조회
        notice = Notice.objects.get(id=notice_id)

        # 제목과 내용, 갱신 시간 변경하고 저장
        notice.notice_title = data['notice_title']
        notice.notice_content = data['notice_content']
        notice.updated_date = timezone.now()

        notice.save(update_fields=["notice_title", "notice_content", "updated_date"])

        # 기존 공지사항 정보 update 후, 공지사항 리스트 페이지로 redirect
        return redirect('manager-notice')


class DeleteNoticeView(View):
    # 공지사항 삭제를 위한 뷰
    def get(self, request):
        # 03/07 - 공지사항 리스트에서 체크한 게시물들을 한 번에 가져올 방법을 생각해보자
        # 삭제할 공지사항들의 id를 통해 해당 객체들을 가져옴(dict 타입)
        notices = Notice.objects.filter(id=request.GET['id'])

        # 위 공지사항들의 status를 0으로 만들어 화면에 뿌리지 않게 만들고, 변동 사항을 저장함
        for notice in notices:
            notice.notice_status = 0
            notice.updated_date = timezone.now()
            notice.save(update_fields=["notice_status", "updated_date"])

        # 상태 업데이트 후 공지사항 리스트 페이지로 redirect
        return redirect('manager-notice')


class DeleteManyNoticeView(APIView):
    # 한 번에 여러 개의 공지사항을 삭제(소프트 딜리트)하는 뷰
    def patch(self, request, notice_ids):
        # 요청 경로에 담긴 notice_ids를 콤마(,)를 기준으로 분리해서 list로 만듬
        notice_ids = notice_ids.split(',')

        # 위 list의 각 요소를 순회
        for notice_id in notice_ids:
            # 요소가 빈 문자열이 아닐 때만 tbl_notice에서 해당 id를 가진 객체를 가져옴
            if notice_id != '':
                notice = Notice.objects.get(id=notice_id)

                # 해당 객체의 status를 0으로 만들고, 변경 시간과 같이 저장
                notice.notice_status = 0
                notice.updated_date = timezone.now()
                notice.save(update_fields=["notice_status", "updated_date"])

        return Response('성공')


# QnA 관리
class QnAManagementView(View):
    # QnA 내역 페이지 이동 뷰
    def get(self, request):
        # 현재 작성된 공지사항 및 QnA의 개수를 세서 dict 데이터로 통합
        notice_count = Notice.enabled_objects.count()
        qna_count = QnA.enabled_objects.count()

        context = {
            'notice_count': notice_count,
            'qna_count': qna_count
        }

        # 공지사항과 QnA 개수를 화면에 전달
        # QnA 내역을 가져오는 것은 별도의 API가 해줌
        return render(request, 'manager/manager-notice/manager-qna/manager-qna.html', context)


class WriteQnAView(View):
    # QnA 작성 페이지 이동 뷰
    def get(self, request):
        # 로그인 검사는 미들웨어가 해주기 때문에, 별도의 정보 필요 없이 바로 render
        return render(request, 'manager/manager-notice/manager-qna/manager-qna-compose.html')

    # QnA 작성 완료 이후의 뷰
    @transaction.atomic
    def post(self, request):
        # POST 방식으로 요청한 데이터를 가져옴
        qna_data = request.POST

        # 받아온 데이터에서 특정 정보(id, 제목, 내용)를 가져와서 dict 타입으로 저장
        data = {
            'qna_title': qna_data['qna-title'],
            'qna_content': qna_data['qna-content'],
        }

        # 받아온 데이터로 tbl_qna에 실행할 insert 쿼리 작성
        QnA.objects.create(**data)

        # 작성한 공지사항 저장 후, QnA 리스트 페이지로 redirect
        return redirect('manager-qna')


class UpdateQnAView(View):
    # QnA 수정 페이지 이동 뷰
    def get(self, request):
        # 수정 버튼에서 전달한 id를 통해 수정할 공지사항 객체 가져오기
        qna = QnA.objects.get(id=request.GET['id'])

        # 수정 페이지에 전달할 QnA의 dict 타입의 데이터 생성
        context = {
            'qna': qna
        }

        # QnA 데이터를 가지고 수정 페이지로 이동
        return render(request, 'manager/manager-notice/manager-qna/manager-qna-modify.html', context)

    # QnA 수정 완료 이후의 뷰
    @transaction.atomic
    def post(self, request):
        # GET 방식으로 url에서 id를 가져옴
        qna_id = request.GET['id']

        # POST 방식으로 받은 id와 제목과 내용도 가져옴
        data = request.POST

        data = {
            'qna_title': data['qna-title'],
            'qna_content': data['qna-content']
        }

        # 가져온 id로 수정할 QnA 조회
        qna = QnA.objects.get(id=qna_id)

        # 제목과 내용, 갱신 시간 변경하고 저장
        qna.qna_title = data['qna_title']
        qna.qna_content = data['qna_content']
        qna.updated_date = timezone.now()

        qna.save(update_fields=["qna_title", "qna_content", "updated_date"])

        # 기존 QnA 정보 update 후, QnA 리스트 페이지로 redirect
        return redirect('manager-qna')


class DeleteQnAView(View):
    # QnA 삭제를 위한 뷰
    def get(self, request):
        # 삭제할 QnA들의 id를 통해 해당 객체들을 가져옴
        qnas = QnA.objects.filter(id=request.GET['id'])

        # 위 QnA 전체를 소프트 딜리트(status = 0)
        for qna in qnas:
            qna.qna_status = 0
            qna.updated_date = timezone.now()
            qna.save(update_fields=["qna_status", "updated_date"])

        # 상태 업데이트 후 QnA 리스트 페이지로 redirect
        return redirect('manager-qna')


class DeleteManyQnAView(APIView):
    # 한 번에 여러 개의 QnA을 삭제(소프트 딜리트)하는 뷰
    def patch(self, request, qna_ids):
        # 요청 경로에 담긴 qna_ids를 콤마(,)를 기준으로 분리해서 list로 만듬
        qna_ids = qna_ids.split(',')

        # 위 list의 각 요소를 순회
        for qna_id in qna_ids:
            # 요소가 빈 문자열이 아닐 때만 tbl_qna에서 해당 id를 가진 객체를 가져옴
            if qna_id != '':
                qna = QnA.objects.get(id=qna_id)

                # 해당 객체의 status를 0으로 만들고, 변경 시간과 같이 저장
                qna.qna_status = 0
                qna.updated_date = timezone.now()
                qna.save(update_fields=["qna_status", "updated_date"])

        return Response('성공')


# 신고 내역 관리
class ReportManagementView(View):
    # 신고 내역 페이지 이동 뷰
    def get(self, request):
        # 신고 내역 전부 가져오기
        return render(request, 'manager/report/report.html')

    # 신고 내역 처리 or 삭제(반려) 후의 뷰
    # 이 페이지는 별도의 신고 상세 모달 또는 페이지를 제작하는 등의 개선이 필요해 보임
    def post(self, request):
        # update 완료 후, 다시 신고 내역 페이지로 이동
        return render(request, 'manager/report/report.html')

# 남은 것들
# 필요한 곳에 API 사용
# 내역 삭제 뷰 post 쓰지 말고 따로 분리할 지 회의
