from django.http import JsonResponse
from users.models import User  

def search_student(request):
    q = request.GET.get("q")
    class_name = request.GET.get("class")

    students = User.objects.filter(role="student")

    if class_name:
        students = students.filter(student_class__name__icontains=class_name)

    if q:
        students = students.filter(first_name__icontains=q) | \
                   students.filter(surname__icontains=q)

    data = [
        {
            "id": s.id,
            "name": f"{s.surname} {s.first_name}",
            "reg_no": s.registration_number,
        }
        for s in students[:20]
    ]

    return JsonResponse({"results": data})


def verify_student(request):
    reg_no = request.GET.get("reg_no")

    try:
        s = User.objects.get(registration_number=reg_no)
        request.session["student_id"] = s.id
        return JsonResponse({"exists": True, "name": f"{s.surname} {s.first_name}"})
    except User.DoesNotExist:
        return JsonResponse({"exists": False})
