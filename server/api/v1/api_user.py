from flask_restful import Resource, reqparse
from server.controllers.tickets import *
from server.controllers.users import *
from server.api.v1 import return_failure, return_success, require_login

USER_PARSER = reqparse.RequestParser(bundle_errors=True)


class UserRetrieveUser(Resource):
    def get(self):
        return return_failure("Please use post requests")

    @require_login(USER_PARSER)
    def post(self, data, user):
        ticket = user_get_ticket(user)
        # tickets = get_claimable_tickets(user, override=True)
        if ticket != None:
            total_tickets, current_position = get_ticket_queue_position(user, ticket.id)
        else:
            total_tickets, current_position = 0, 0
        # total_tickets = len(tickets) if tickets is not None else 0
        # current_position = total_tickets
        # for i, t in enumerate(tickets):
        #     if t == ticket:
        #         current_position = i
        #         break
        return return_success({
            'ticket': ticket.json() if ticket is not None else None,
            'queue_position': current_position,
            'queue_length': total_tickets,
            'rankings': mentor_rankings(),
            'user': user.json()
        })


class UserRetrieveAdmin(Resource):
    def get(self):
        return return_failure("Please use post requests")

    @require_login(USER_PARSER)
    def post(self, data, user):
        ticket, team = user_get_claim_ticket(user)
        tickets = get_claimable_tickets(user)
        total_tickets = len(tickets) if tickets is not None else 0
        return return_success({
            'ticket': ticket.json(team) if ticket is not None else None,
            'tickets': [t[0].json(t[1]) for t in tickets],
            'queue_length': total_tickets,
            'rankings': mentor_rankings(),
            'user': user.json()
        })


USER_UPDATE_PARSER = reqparse.RequestParser(bundle_errors=True)
USER_UPDATE_PARSER.add_argument('name',
                                help='Need name',
                                required=True)
USER_UPDATE_PARSER.add_argument('affiliation',
                                help='Needs affiliation',
                                required=True)
USER_UPDATE_PARSER.add_argument('team',
                                help='Needs team',
                                required=True)
USER_UPDATE_PARSER.add_argument('skills',
                                help='Need skills',
                                required=True)


class UserProfileUpdate(Resource):
    @require_login(USER_UPDATE_PARSER)
    def post(self, data, user):
        if not user.mentor_is and not validate_team_name(data['team']):
            return return_failure("Invalid Team name")
            
        set_name(user, data['name'])
        set_affiliation(user, data['affiliation'])
        set_team(user, data['team'])
        set_skills(user, data['skills'])
        return return_success({
            'user': user.json()
        })


class UserHackerDashStats(Resource):
    @require_login(USER_PARSER)
    def post(self, data, user):
        return return_success({
            'stats': {
                'countMentors': get_mentors_online(),
                'estimates': estimated_ticket_stats()['estimates']
            }
        })


TEST_PARSER = reqparse.RequestParser(bundle_errors=True)
TEST_PARSER.add_argument('id', help='Need id', required=True, type=int)


class UserDashboard(Resource):
    def post(self):
        req = TEST_PARSER.parse_args()
        user = get_user_by_id(req['id'])
        
        data = get_user_ticket_dash(user)
        data['rankings'] = mentor_rankings() if user.mentor_is else None
        data['stats']['countMentors'] = get_mentors_online()
        
        return return_success(data)


class UserDashboardA(Resource):
    def post(self):
        req = TEST_PARSER.parse_args()
        user = get_user_by_id(req['id'])
        
        return return_success({
            'stats': {
                'countMentors': get_mentors_online(),
                'estimates': estimated_ticket_stats()['estimates']
            }
        })

class UserDashboardB(Resource):
    def post(self):
        req = TEST_PARSER.parse_args()
        user = get_user_by_id(req['id'])
        
        ticket = user_get_ticket(user)
        if ticket != None:
            total_tickets, current_position = get_ticket_queue_position(user, ticket.id)
        else:
            total_tickets, current_position = 0, 0

        return return_success({
            'ticket': ticket.json() if ticket is not None else None,
            'queue_position': current_position,
            'queue_length': total_tickets,
            'rankings': mentor_rankings(),
            'user': user.json()
        })