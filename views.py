from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Publication
import bibtexparser
from datetime import datetime
import re

def format_apa_citation(publication):
    """Convert publication data to APA format."""
    # Format authors
    authors = publication.authors.split(' and ')
    if len(authors) > 1:
        formatted_authors = ', '.join(authors[:-1]) + ', & ' + authors[-1]
    else:
        formatted_authors = authors[0]

    # Format date
    year = publication.date.year if publication.date else 'n.d.'

    # Format title
    title = publication.title.strip('{}')
    if not title.endswith(('.', '!', '?')):
        title += '.'

    # Format journal
    journal = publication.journal.strip('{}')
    if journal:
        journal = f"<i>{journal}</i>"

    # Format DOI
    doi = f"https://doi.org/{publication.doi}" if publication.doi else None

    # Combine all parts
    citation = f"{formatted_authors} ({year}). {title} {journal}"
    
    if doi:
        citation += f" <a href='{doi}' target='_blank'>DOI: {publication.doi}</a>"
    elif publication.url:
        citation += f" <a href='{publication.url}' target='_blank'>[Link]</a>"

    return citation

@staff_member_required
def publication_management(request):
    if request.method == 'POST':
        if 'bibtex_file' in request.FILES:
            # Handle BibTeX file upload
            bibtex_file = request.FILES['bibtex_file']
            bibtex_str = bibtex_file.read().decode('utf-8')
            process_bibtex(bibtex_str, request)
        elif 'bibtex_text' in request.POST:
            # Handle pasted BibTeX text
            bibtex_str = request.POST['bibtex_text']
            process_bibtex(bibtex_str, request)
        else:
            # Handle manual entry
            try:
                Publication.objects.create(
                    title=request.POST['title'],
                    authors=request.POST['authors'],
                    journal=request.POST['journal'],
                    date=request.POST['date'],
                    doi=request.POST.get('doi', ''),
                    url=request.POST.get('url', '')
                )
                messages.success(request, 'Publication added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding publication: {str(e)}')

    publications = Publication.objects.all().order_by('-date')
    # Add APA formatted citations
    for pub in publications:
        pub.apa_citation = format_apa_citation(pub)
    
    return render(request, 'admin/publication_management.html', {
        'publications': publications
    })

def process_bibtex(bibtex_str, request):
    try:
        # Parse BibTeX
        parser = bibtexparser.bparser.BibTexParser()
        bib_database = bibtexparser.loads(bibtex_str, parser=parser)

        # Process each entry
        for entry in bib_database.entries:
            # Convert BibTeX date to Python date
            date_str = entry.get('year', '')
            if date_str:
                try:
                    date = datetime.strptime(date_str, '%Y').date()
                except ValueError:
                    date = None
            else:
                date = None

            # Create publication
            Publication.objects.create(
                title=entry.get('title', '').strip('{}'),
                authors=entry.get('author', '').strip('{}'),
                journal=entry.get('journal', '').strip('{}') or entry.get('booktitle', '').strip('{}'),
                date=date,
                doi=entry.get('doi', ''),
                url=entry.get('url', '')
            )

        messages.success(request, f'Successfully imported {len(bib_database.entries)} publications.')
    except Exception as e:
        messages.error(request, f'Error processing BibTeX: {str(e)}') 