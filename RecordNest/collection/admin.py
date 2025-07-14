from django.contrib import admin
from .models import UserRecord, RecordList, Tag

@admin.register(UserRecord)
class UserRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'user')
    search_fields = ('title', 'artists')

@admin.register(RecordList)
class RecordListAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)