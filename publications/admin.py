from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Publication

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors', 'journal', 'year', 'volume', 'number', 'doi', 'import_bibtex_link')
    list_filter = ('year', 'journal', 'bibtex_type')
    search_fields = ('title', 'authors', 'journal', 'abstract', 'bibtex_key')
    readonly_fields = ('created_at', 'updated_at', 'apa_citation')
    fieldsets = (
        (None, {
            'fields': ('title', 'authors', 'journal', 'date', 'year')
        }),
        ('Publication Details', {
            'fields': ('volume', 'number', 'pages', 'doi', 'url', 'abstract')
        }),
        ('BibTeX Information', {
            'fields': ('bibtex_key', 'bibtex_type')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Citation', {
            'fields': ('apa_citation',),
            'classes': ('collapse',)
        })
    )
    
    def import_bibtex_link(self, obj):
        url = reverse('publications:import_bibtex')
        return format_html('<a href="{}" class="button">Import BibTeX</a>', url)
    import_bibtex_link.short_description = 'Import BibTeX'
    import_bibtex_link.allow_tags = True 