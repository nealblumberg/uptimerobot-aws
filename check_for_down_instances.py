import new_functions as x
import logging,os

def main():

    dirpath = os.path.dirname(__file__)
    filepath = os.path.join(dirpath, 'DownInstance.log')

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=filepath,
                        filemode='a')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)



    servers_to_be_reset = x.reset_reboot_tags()
    if len(servers_to_be_reset) > 0:

        print('resetting tags for: ' )
    else:
        print("No server tags reset")



    down_sites = x.get_sites_status('down')



    if (len(down_sites)) > 0:

        for site,down_time in down_sites.items():

            print(site)
            print(down_time)

            if x.check_time_to_reboot(down_time=down_time):
                if x.check_instance_reboot_tag(site) == 'TRUE':
                    print('Already rebooting')
                else:
                    print('Time to reboot')
                    logging.info("REBOOTING SITE: " + site)
                    if x.reboot_down_instance(site):
                        logging.info("REBOOTING SITE " + site + " SUCCESSFUL")
                        x.update_reboot_tag(site,'TRUE')
                        x.email_results(site)
                    else:
                        logging.info("REBOOTING SITE " + site + " FAILED")
                        x.email_results(site,status='fail')
            else:
                print("not time to reboot yet")

    else:
        print("all sites good")
if __name__ == '__main__':
    main()