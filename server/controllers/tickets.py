from server.models.ticket import Ticket
from server.models.user import User
from server.app import db
from typing import cast
import datetime
from sqlalchemy import or_, and_
from server.cache import should_cache_function

from sqlalchemy import func, select
from flask import current_app

from sqlalchemy.sql.expression import literal
from sqlalchemy.orm import aliased

import json

def tuple_to_ticket_json(tuple):
    if tuple['id'] == None:
        return None

    now = datetime.datetime.now()
    return {
        "id": tuple['id'],
        "data": json.loads(tuple['data']),
        "uid": tuple['uid'],
        "status": tuple['status'],
        "requested_by": tuple['requestor'],
        "claimed_by": tuple['claimant'],
        "minutes": (now-tuple['date_created']).total_seconds()//60,
        "team": tuple['team']
    }


# Mentor rankings update every 60 seconds
@should_cache_function("ticket_stats", 60)
def ticket_stats():
    tickets = Ticket.query.filter(
        or_(Ticket.status == 3, Ticket.status == 5)).all()
    if len(tickets) == 0:
        return {
            'average_wait': 0,
            'average_claimed': 0,
            'average_rating': 0
        }

    wait_total = 0
    claimed_total = 0
    rating_total = 0
    for ticket in tickets:
        wait_total += ticket.total_unclaimed_seconds
        claimed_total += ticket.total_claimed_seconds
        rating_total += ticket.rating
    return {
        'average_wait': wait_total / len(tickets),
        'average_claimed': claimed_total / len(tickets),
        'average_rating': rating_total / len(tickets)
    }

def get_claimable_tickets(user, override=False):
    if not user.mentor_is and not override:
        return []
    tickets = db.session.query(Ticket, User.team)\
        .join(User, User.id == Ticket.requestor_id)\
        .filter(or_(Ticket.status == 0, Ticket.status == 2)).order_by(Ticket.id).all()
    # tickets = Ticket.query.filter(
    #     or_(Ticket.status == 0, Ticket.status == 2)).order_by(Ticket.id).all()
    return tickets


def get_ticket_queue_position(user, ticket_id):
    # s = select([
    #     func.row_number().over(order_by=desc(Ticket.id)).label('queue_number')
    # ])
    inner_select = db.session.query(Ticket.id.label('id'), func.count().over().label('total'), func.row_number().over(order_by=Ticket.id).label('q_pos'))\
        .filter(or_(Ticket.status == 0, Ticket.status == 2)).order_by(Ticket.id).subquery()

    res = db.session.query(inner_select.c.total, inner_select.c.q_pos)\
        .filter(inner_select.c.id == ticket_id).all()
    # res = db.session.query(func.count().over().label('total'), func.row_number().over(order_by=desc(Ticket.id)).label('q_pos'))\
    #     .filter(and_(
    #         or_(Ticket.status == 0, Ticket.status == 2),
    #         Ticket.id == ticket_id)).order_by(Ticket.id).one()
    
    # print(res)
    return (None, None,) if len(res) == 0 else res[0]


def get_ticket(ticket_id):
    ticket = Ticket.query.filter_by(
        id=ticket_id).first()
    return ticket


def create_ticket(user, data):
    """
    Creates ticket with a data dictionary field
    Returns ticket or None if failed
    """
    if (Ticket.query.filter(and_(Ticket.requestor == user, Ticket.status < 3)).count() > 0):
        return None
    ticket = Ticket(user, data)
    db.session.add(ticket)
    db.session.commit()
    return ticket


def claim_ticket(user, ticket):
    """
    returns true if successful
    """
    # only mentors / admins can claim
    if (not user.mentor_is and not user.admin_is):
        return False

    now = datetime.datetime.now()
    if (ticket.status == 0 or ticket.status == 2):
        # ticket is currently able to be claimed
        ticket.total_unclaimed_seconds += (now -
                                           ticket.date_updated).total_seconds()
        ticket.claimant = user
        ticket.date_updated = now
        ticket.status = 1
        db.session.commit()
        return True
    return False

def unclaim_ticket(user, ticket):
    now = datetime.datetime.now()

    # Claimant has to be same user and actually claimed (and not closed)
    if ticket.claimant != user or ticket.status != 1:
        return False

    ticket.total_claimed_seconds += (now-ticket.date_updated).total_seconds()
    ticket.claimant = None
    ticket.date_updated = now
    ticket.status = 2
    db.session.commit()
    return True


def cancel_ticket(user, ticket):
    now = datetime.datetime.now()

    # since ticket was never claimed then we don't do anything
    # You can only cancel ticket if the ticket is not already dead
    if ticket.status < 3:
        # Only the requester (or admin) can close
        if (ticket.requestor != user and not user.admin_is):
            return False
        ticket.status = 4
        ticket.date_updated = now
        db.session.commit()
        return True
    return False


def close_ticket(user, ticket):
    now = datetime.datetime.now()
    # only mentors can close
    if (not user.mentor_is and not user.admin_is):
        return False
    if (ticket.claimant == user):
        ticket.total_claimed_seconds += (now -
                                         ticket.date_updated).total_seconds()
        ticket.status = 3
        ticket.date_updated = now
        db.session.commit()
        return True
    return False

def rate_ticket(user, ticket, rating):
    now = datetime.datetime.now()

    # Requestor has to be same user and actually closed
    if ticket.requestor != user or ticket.status != 3:
        return False

    ticket.rating = rating
    # Completely closed and rated now!
    ticket.status = 5
    ticket.date_updated = now
    db.session.commit()
    return True

def estimated_ticket_stats():
    row = db.session.query(
                func.percentile_cont(0.5).
                    within_group(Ticket.total_unclaimed_seconds).
                    label('estResponse'),
                func.percentile_cont(0.5).
                    within_group(Ticket.total_claimed_seconds).
                    label('estCompletion'))\
            .filter(or_(Ticket.status == 3, Ticket.status == 5))\
            .one()

    return {
        'estimates': {
            'estResponse': row[0],
            'estCompletion': row[1]
        }
    }
    

def get_user_ticket_dash(user):
    queue = db.session.query(
            Ticket.requestor_id.label('user_in_line'),
            func.count().over().label('total'),
            func.row_number().over(order_by=Ticket.id).label('q_pos'))\
        .filter(or_(Ticket.status == 0, Ticket.status == 2)).order_by(Ticket.id).subquery()
    
    queue_stats = db.session.query(queue.c.total, queue.c.q_pos)\
        .filter(queue.c.user_in_line == user.id).subquery()

    Requestor = aliased(User)
    Claimant = aliased(User)

    current_ticket = db.session.query(Ticket, Requestor.name.label('requestor'), Claimant.name.label('claimant'), Requestor.team.label('team'))\
        .join(Requestor, Ticket.requestor_id == Requestor.id)\
        .outerjoin(Claimant, Ticket.claimant_id == Claimant.id)\
        .filter(and_(Ticket.requestor_id == user.id, Ticket.status < 4))\
        .subquery()
    
    ticket_info = db.session.query(current_ticket, queue_stats).outerjoin(queue_stats, literal(True)).subquery()

    fin_stats = db.session.query(
                func.percentile_cont(0.5).
                    within_group(Ticket.total_unclaimed_seconds).
                    label('estResponse'),
                func.percentile_cont(0.5).
                    within_group(Ticket.total_claimed_seconds).
                    label('estCompletion'))\
            .filter(or_(Ticket.status == 3, Ticket.status == 5)).subquery()
            
    dash_stats = db.session.query(fin_stats, ticket_info).outerjoin(ticket_info, literal(True)).all()
    
    # print(dash_stats[0]._asdict())
    tuple = dash_stats[0]._asdict()
    return {
        'ticket': tuple_to_ticket_json(tuple),
        'queue_position': tuple['q_pos'],
        'queue_length': tuple['total'],
        # 'rankings': ,
        'user': user.json(),
        'stats': {
            'estimates': {
                'estResponse': tuple['estResponse'],
                'estCompletion': tuple['estCompletion']
            }
        }
    }
    
    
    # inner_select = db.session.query(
    #         # Ticket, User.team.label('team'), User.name.label('requestor'),
    #         Ticket.requestor_id.label('requestor_id'),
    #         func.count().over().label('total'),
    #         func.row_number().over(order_by=Ticket.id).label('q_pos'))\
    #     .filter(or_(Ticket.status == 0, Ticket.status == 2)).order_by(Ticket.id).subquery()
    
    # # inner_select_1 = db.session.query(
    # #     inner_select, User.name.label('claimant')
    # # ).outerjoin(User, inner_select.c.claimant_id == User.id).subquery()

    # fin_stats = db.session.query(
    #             func.percentile_cont(0.5).
    #                 within_group(Ticket.total_unclaimed_seconds).
    #                 label('estResponse'),
    #             func.percentile_cont(0.5).
    #                 within_group(Ticket.total_claimed_seconds).
    #                 label('estCompletion'))\
    #         .filter(or_(Ticket.status == 3, Ticket.status == 5)).subquery()

    # # ticket_stats = db.session.query(inner_select_1)\
    # #     .filter(inner_select_1.c.requestor_id == user.id).subquery()

    # ticket_stats = db.session.query(inner_select)\
    #     .filter(inner_select.c.requestor_id == user.id).subquery()

    # res = db.session.query(fin_stats, ticket_stats).all()
    # print(res[0]._asdict())
    
    # # res = db.session.query(func.count().over().label('total'), func.row_number().over(order_by=desc(Ticket.id)).label('q_pos'))\
    # #     .filter(and_(
    # #         or_(Ticket.status == 0, Ticket.status == 2),
    # #         Ticket.id == ticket_id)).order_by(Ticket.id).one()
    
    # # print(res)
    # # return (None, None,) if len(res) == 0 else res[0]