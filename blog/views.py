from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.db.models import Count
from taggit.models import Tag

from .models import Post, Comment
from .forms import EmailPostForm, CommentForm


############################# Function Based Views #############################
def post_list(request, tag_slug=None):
    posts_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        posts_list = posts_list.filter(tags__in=[tag])

    # Pagination with 3 posts per page
    paginator = Paginator(posts_list, 3)
    page_num = request.GET.get("page", 1)
    try:
        posts = paginator.page(page_num)
    except PageNotAnInteger:
        # if page number is not an integer, deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # if page number is out of range, deliver last page of result
        posts = paginator.page(paginator.num_pages)

    return render(
        request,
        "blog/post/list.xhtml",
        {"posts": posts, "tag": tag},
    )


def post_detail(request, year, month, day, slug_value):
    # try:
    #     post = Post.published.get(id=id)
    # except Post.DoesNotExist:
    #     raise Http404("No Post Found.")

    # post = get_object_or_404(Post, id=id, status=Post.Status.PUBLISHED)

    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=slug_value,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    # list active comments for this post
    comments = post.comments.filter(active=True)
    # form for users to comment
    form = CommentForm()
    # list of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-publish"
    )[:4]

    return render(
        request,
        "blog/post/detail.xhtml",
        {
            "post": post,
            "comments": comments,
            "form": form,
            "similar_posts": similar_posts,
        },
    )


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None

    form = CommentForm(data=request.POST)

    if form.is_valid():
        # create a comment object without saving it to the db
        comment = form.save(commit=False)
        # assign the post to the comment
        comment.post = post
        # save the comment object to the db
        comment.save()

    return render(
        request,
        "blog/post/comment.xhtml",
        {"post": post, "form": form, "comment": comment},
    )


def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False

    if request.method == "POST":
        # form was submitted
        form = EmailPostForm(request.POST)

        if form.is_valid():
            # form fields passed validation
            cd = form.cleaned_data

            # send email
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read {post.title}"
            message = f"Read {post.title} at {post_url}\n\n{cd['name']}'s comments: {cd['comments']}"

            # send_mail(subject, message, "micpac184@gmail.com", [cd["to"]])
            send_mail(subject, message, cd["email"], [cd["to"]])
            sent = True
    else:
        form = EmailPostForm()

    return render(
        request,
        "blog/post/share.xhtml",
        {"post": post, "form": form, "sent": sent},
    )


############################## Class Based Views ##############################
from django.views.generic import ListView


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = "posts"
    paginate_by = 3
    template_name = "blog/post/list.xhtml"
