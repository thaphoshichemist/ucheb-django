from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm, SearchForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity

#from django.http import Http404

def post_share(request, post_id):
    #izvlech post po id
    post = get_object_or_404(Post,
                             id=post_id,
                             status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':
        #Forma bila peredana na obrabotku
        form = EmailPostForm(request.POST)
        if form.is_valid():
            #Polya formi uspeshmo proshli validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(
                post.get_absolute_url())
            subject = f"{cd['name']} recommends you read" \
                      f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n" \
                      f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'your_account@gmail.com',
                      [cd['to']])
            sent = True
            # ... send email
    else:
            form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,
                                                        'form': form,
                                                        'sent': sent})

@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post,
                             id=post_id,
                             status=Post.Status.PUBLISHED)
    comment = None
    # Comment sent
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Create object class Comment, don't save in DB
        comment = form.save(commit=False)
        # Naznach post commetu
        comment.post = post
        # Save in DB
        comment.save()
    return render(request, 'blog/post/comment.html',
                  {'post': post,
                   'form': form,
                   'comment': comment})

# Create your views here.i
#class PostListView(ListView):
#    """
   #     alternative view post list
#    """
#    queryset = Post.published.all()
#    context_object_name = 'posts'
#    paginate_by = 3
#    template_name = 'blog/post/list.html'

def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # Razbivka s 3 postami na stranicu
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # ecli ne celoe chislo, to vidaet pervuiu stranicu
        posts = paginator.page(1)
    except EmptyPage:
        #ecli vne diapazona, to vidaet poslednuu stranicu
        posts = paginator.page(paginator.num_pages)
    return render(request,
                  'blog/post/list.html',
                  {'posts': posts,
                   'tag': tag})

def post_detail(request, year, month, day, post):
    #try:
     #   post = Post.published.get(id=id)
    #except Post.DoesNotExist:
     #   raise Http404("No Post Found")
    post = get_object_or_404(Post, 
                             status= Post.Status.PUBLISHED,
                             slug=post,
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    # Comments active list for post
    comments = post.comments.filter(active=True)
    # Form for users commenting 
    form = CommentForm()

    # list of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids)\
                                    .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
                                .order_by('-same_tags', '-publish')[:4]
    return render(request,
                  'blog/post/detail.html',
                  {'post': post,
                   'comments': comments,
                   'form': form,
                   'similar_posts': similar_posts})


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.annotate(
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
    
    return render(request,
                    'blog/post/search.html',
                    {'form': form,
                    'query': query,
                    'results': results})
