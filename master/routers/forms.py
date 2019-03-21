#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/16
# @Author: lsj
# @File  : forms.py
# @Desc  : 
默认Python版本支持：3.6
"""
from flask_pagedown.fields import PageDownField
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import TextAreaField, SelectField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo

from master.models import UsersModel, RolesModel


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')
    pass


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Length(1, 64), Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp(
            '^[A-Za-z][A-Za-z0-9_.]*$', 0,
            'Username must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if UsersModel.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if UsersModel.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

    pass


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm new password', validators=[
        DataRequired()])
    submit = SubmitField('Update Password')
    pass


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('Reset Password')
    pass


class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')
    pass


class ChangeEmailForm(FlaskForm):
    email = StringField('New Email', validators=[
        DataRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if UsersModel.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    pass


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')
    pass


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')
    pass


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Length(1, 64), Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp(
            '^[A-Za-z][A-Za-z0-9_.]*$', 0,
            'Username must have only letters, numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role')  # , coerce=int
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        roles = RolesModel.query.order_by(RolesModel.name).all()
        self.role.choices = [(role.id, role.name) for role in roles]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                UsersModel.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                UsersModel.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

    pass


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('Submit')
    pass


class CommentForm(FlaskForm):
    body = StringField('Enter your comment', validators=[DataRequired()])
    submit = SubmitField('Submit')
    pass


class NodeForm(FlaskForm):
    group_name = StringField("Group Name")
    node_host = StringField("Node Host", validators=[
        DataRequired(), Regexp(
            "^((\d|[1-9]\d|1\d{2}|2[0-5][0-5])\.){3}"
            "(\d|[1-9]\d|1\d{2}|2[0-5][0-5])$", 0,
            'Username must have only letters, numbers, dots or underscores')])
    node_port = StringField('Node Port', validators=[
        DataRequired(), Length(1, 64), Regexp(
            "^([0-9]|[1-9]\d{1,3}|[1-5]\d{4}|6[0-5]{2}[0-3][0-5])$", 0,
            'Username must have only letters, numbers, dots or underscores')])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp(
            '^[A-Za-z][A-Za-z0-9_.]*$', 0,
            'Username must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if UsersModel.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if UsersModel.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

    pass
