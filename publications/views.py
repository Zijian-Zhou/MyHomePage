import bibtexparser
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.translation import gettext as _
from datetime import datetime
from .models import Publication

@staff_member_required
def import_bibtex(request):
    if request.method == 'POST':
        import_type = request.POST.get('import_type')
        bibtex_text = None
        
        if import_type == 'file':
            if 'bibtex_file' not in request.FILES:
                messages.error(request, _('Please select a BibTeX file.'))
                return render(request, 'admin/publication/bibtex_import.html')
            
            file = request.FILES['bibtex_file']
            if not file.name.endswith('.bib'):
                messages.error(request, _('Please upload a valid BibTeX file (.bib).'))
                return render(request, 'admin/publication/bibtex_import.html')
            
            try:
                bibtex_text = file.read().decode('utf-8')
            except UnicodeDecodeError:
                messages.error(request, _('Error reading file. Please ensure it is a valid text file.'))
                return render(request, 'admin/publication/bibtex_import.html')
        
        elif import_type == 'text':
            bibtex_text = request.POST.get('bibtex_text')
            if not bibtex_text:
                messages.error(request, _('Please enter BibTeX entries.'))
                return render(request, 'admin/publication/bibtex_import.html')
        
        if bibtex_text:
            try:
                parser = bibtexparser.bparser.BibTexParser(common_strings=True)
                bib_database = bibtexparser.loads(bibtex_text, parser=parser)
                
                imported_count = 0
                error_count = 0
                for entry in bib_database.entries:
                    try:
                        # Handle date
                        year = entry.get('year', '')
                        month = entry.get('month', '1')  # Default to January if no month
                        try:
                            # Try to parse the date
                            if month.isdigit():
                                date = datetime.strptime(f"{year}-{month}-1", "%Y-%m-%d").date()
                            else:
                                # Handle month names
                                date = datetime.strptime(f"{year} {month} 1", "%Y %B %d").date()
                        except (ValueError, AttributeError):
                            # If date parsing fails, use January 1st of the year
                            try:
                                date = datetime.strptime(f"{year}-1-1", "%Y-%m-%d").date()
                            except ValueError:
                                # If year is invalid, use current date
                                date = datetime.now().date()

                        # Create or update publication
                        publication, created = Publication.objects.update_or_create(
                            bibtex_key=entry.get('ID', ''),
                            defaults={
                                'title': entry.get('title', '').strip('{}'),
                                'authors': entry.get('author', '').strip('{}'),
                                'year': year,
                                'journal': entry.get('journal', '').strip('{}') or entry.get('booktitle', '').strip('{}'),
                                'date': date,
                                'volume': entry.get('volume', ''),
                                'number': entry.get('number', ''),
                                'pages': entry.get('pages', ''),
                                'doi': entry.get('doi', ''),
                                'url': entry.get('url', ''),
                                'abstract': entry.get('abstract', ''),
                                'bibtex_type': entry.get('ENTRYTYPE', ''),
                            }
                        )
                        imported_count += 1
                    except Exception as e:
                        error_count += 1
                        messages.warning(request, _(f'Error importing entry: {str(e)}'))
                        continue
                
                if imported_count > 0:
                    messages.success(request, _(f'Successfully imported {imported_count} publications.'))
                if error_count > 0:
                    messages.warning(request, _(f'Failed to import {error_count} publications.'))
            
            except Exception as e:
                messages.error(request, _(f'Error parsing BibTeX: {str(e)}'))
    
    return render(request, 'admin/publication/bibtex_import.html') 